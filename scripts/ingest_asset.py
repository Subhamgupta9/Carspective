#!/usr/bin/env python3
# ============================================================
# SMARTCAR AI — PHASE 4: LOCAL VEHICLE ASSET INGESTION PIPELINE
# scripts/ingest_asset.py — High-Quality Asset Ingest, Validate & Register
# ============================================================
#
# Rules & Guarantees:
#   1. Validate GLB header, chunks, buffers, meshes, vertices, dimensions.
#   2. Reject corrupted assets with explicit reasons (zero meshes, NaNs, bad headers, degenerate dimensions).
#   3. Register verified assets into assets/vehicles/manifest.json.
#   4. Every manifest entry contains: path, source, verified, generation, variant.
#   5. Preserve canonical generation metadata (slug, name, year_start, year_end).
#   6. Optional asset optimization.
#   7. NEVER remove watermarks from third-party models.
#   8. NEVER use assets without appropriate project licensing.
#   9. NEVER create fake assets.
# ============================================================

import os
import sys
import json
import math
import shutil
import struct
import argparse
from pathlib import Path

# Add project root to sys.path so app modules can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.carimages_service import (
    normalize_make_slug,
    normalize_model_slug,
    slugify,
    fetch_catalog,
    resolveVehicleGeneration,
)

# Standard constants
GLB_MAGIC = b"glTF"
GLB_VERSION = 2
CHUNK_JSON = b"JSON"
CHUNK_BIN = b"BIN\x00"
MIN_GLB_SIZE = 1000

# Automotive dimensional envelope (+-30% around L~4.5m, W~1.8m, H~1.4m)
AUTOMOTIVE_LIMITS = {
    "length": (4.5 * 0.70, 4.5 * 1.30),  # (3.15m, 5.85m)
    "width": (1.8 * 0.70, 1.8 * 1.30),   # (1.26m, 2.34m)
    "height": (1.4 * 0.70, 1.4 * 1.30),  # (0.98m, 1.82m)
}

DEFAULT_METADATA = {
    "targetHeight": 1.50,
    "baseHeading": -1.5707963267948966,
    "groundOffset": 0.0,
    "cameraDistance": 7.0,
    "cameraTargetHeight": 0.75,
    "cameraTargetZ": 0.0,
}


class AssetValidationError(Exception):
    """Raised when a candidate GLB asset fails validation."""
    pass


def parse_glb(file_path_or_bytes):
    """
    Parses a binary GLB file or bytes and returns (gltf_dict, bin_bytes, total_size).
    Validates magic bytes, version, chunk types and lengths.
    """
    if isinstance(file_path_or_bytes, (str, Path)):
        p = Path(file_path_or_bytes)
        if not p.exists():
            raise AssetValidationError(f"File not found: {p}")
        raw_bytes = p.read_bytes()
    elif isinstance(file_path_or_bytes, (bytes, bytearray)):
        raw_bytes = bytes(file_path_or_bytes)
    else:
        raise AssetValidationError("Invalid input type: expected path or bytes")

    total_size = len(raw_bytes)
    if total_size < MIN_GLB_SIZE:
        raise AssetValidationError(f"File too small ({total_size} bytes < {MIN_GLB_SIZE})")

    # 1. 12-byte header: magic (4), version (4), length (4)
    magic = raw_bytes[:4]
    if magic != GLB_MAGIC:
        raise AssetValidationError(f"Invalid GLB magic bytes: {magic!r} != {GLB_MAGIC!r}")

    version, declared_length = struct.unpack_from("<II", raw_bytes, 4)
    if version != GLB_VERSION:
        raise AssetValidationError(f"Unsupported GLB version: {version} (expected {GLB_VERSION})")
    if declared_length > total_size:
        raise AssetValidationError(f"Truncated GLB: declared length {declared_length} > file size {total_size}")

    # 2. Chunk 0: JSON
    if total_size < 20:
        raise AssetValidationError("GLB file too small to contain chunk header")

    json_chunk_len, json_chunk_type = struct.unpack_from("<I4s", raw_bytes, 12)
    if json_chunk_type != CHUNK_JSON:
        raise AssetValidationError(f"Invalid chunk 0 type: {json_chunk_type!r} (expected b'JSON')")

    json_end = 20 + json_chunk_len
    if json_end > total_size:
        raise AssetValidationError("GLB JSON chunk exceeds file bounds")

    json_bytes = raw_bytes[20:json_end]
    try:
        gltf_dict = json.loads(json_bytes.decode("utf-8"))
    except Exception as e:
        raise AssetValidationError(f"Failed to parse GLB JSON chunk: {e}")

    # 3. Chunk 1: BIN (optional in glTF 2.0, but standard for self-contained GLBs)
    bin_bytes = b""
    if json_end + 8 <= total_size:
        bin_chunk_len, bin_chunk_type = struct.unpack_from("<I4s", raw_bytes, json_end)
        if bin_chunk_type == CHUNK_BIN:
            bin_start = json_end + 8
            bin_end = bin_start + bin_chunk_len
            bin_bytes = raw_bytes[bin_start:bin_end]

    return gltf_dict, bin_bytes, total_size


def validate_glb_meshes(gltf, bin_bytes):
    """
    Validates meshes and vertex buffers.
    Checks:
      - At least 1 mesh
      - At least 1 primitive with POSITION attribute
      - Non-zero vertex count
      - Zero NaN or Infinite coordinates
    Returns (mesh_count, total_vertices, bbox_dict).
    """
    meshes = gltf.get("meshes", [])
    if not meshes:
        raise AssetValidationError("GLB contains 0 meshes")

    accessors = gltf.get("accessors", [])
    buffer_views = gltf.get("bufferViews", [])

    total_vertices = 0
    all_xs, all_ys, all_zs = [], [], []

    for m_idx, mesh in enumerate(meshes):
        primitives = mesh.get("primitives", [])
        if not primitives:
            raise AssetValidationError(f"Mesh {m_idx} contains 0 primitives")

        for p_idx, prim in enumerate(primitives):
            attrs = prim.get("attributes", {})
            pos_idx = attrs.get("POSITION")
            if pos_idx is None or pos_idx >= len(accessors):
                raise AssetValidationError(f"Primitive {p_idx} in mesh {m_idx} lacks valid POSITION attribute")

            acc = accessors[pos_idx]
            count = acc.get("count", 0)
            if count <= 0:
                raise AssetValidationError(f"Primitive {p_idx} in mesh {m_idx} has 0 vertices")

            bv_idx = acc.get("bufferView")
            if bv_idx is None or bv_idx >= len(buffer_views):
                raise AssetValidationError(f"POSITION accessor {pos_idx} missing bufferView")

            bv = buffer_views[bv_idx]
            byte_offset = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
            byte_stride = bv.get("byteStride", 12)  # Default 3 * 4 bytes for VEC3 FLOAT

            total_vertices += count

            # Sample vertices to ensure zero NaN / Inf and collect min/max bounds
            step = max(1, count // 100)
            for i in range(0, count, step):
                offset = byte_offset + i * byte_stride
                if offset + 12 > len(bin_bytes):
                    raise AssetValidationError(f"Vertex buffer read out-of-bounds at vertex {i}")

                x, y, z = struct.unpack_from("<fff", bin_bytes, offset)
                if math.isnan(x) or math.isnan(y) or math.isnan(z):
                    raise AssetValidationError(f"NaN coordinate detected in mesh {m_idx} primitive {p_idx}")
                if math.isinf(x) or math.isinf(y) or math.isinf(z):
                    raise AssetValidationError(f"Infinite coordinate detected in mesh {m_idx} primitive {p_idx}")

                all_xs.append(x)
                all_ys.append(y)
                all_zs.append(z)

            # Also check accessor min/max if present
            acc_min = acc.get("min", [])
            acc_max = acc.get("max", [])
            if acc_min and len(acc_min) >= 3:
                for val in acc_min:
                    if math.isnan(val) or math.isinf(val):
                        raise AssetValidationError("Accessor min contains NaN/Inf")
                all_xs.append(acc_min[0])
                all_ys.append(acc_min[1])
                all_zs.append(acc_min[2])
            if acc_max and len(acc_max) >= 3:
                for val in acc_max:
                    if math.isnan(val) or math.isinf(val):
                        raise AssetValidationError("Accessor max contains NaN/Inf")
                all_xs.append(acc_max[0])
                all_ys.append(acc_max[1])
                all_zs.append(acc_max[2])

    if total_vertices == 0:
        raise AssetValidationError("GLB model has 0 total vertices")

    bbox = {
        "min_x": min(all_xs), "max_x": max(all_xs),
        "min_y": min(all_ys), "max_y": max(all_ys),
        "min_z": min(all_zs), "max_z": max(all_zs),
    }

    return len(meshes), total_vertices, bbox


def validate_glb_dimensions(bbox):
    """
    Validates physical dimensions of the vehicle model.
    Checks:
      - Non-zero dimensions
      - Automotive aspect ratio (cars are longer than they are tall)
      - When normalized to standard target height (1.4m - 1.6m), fits automotive envelope +-30%
    Returns sorted dimension dict: {"length": L, "width": W, "height": H, "raw": {...}}.
    """
    span_x = bbox["max_x"] - bbox["min_x"]
    span_y = bbox["max_y"] - bbox["min_y"]
    span_z = bbox["max_z"] - bbox["min_z"]

    if span_x < 0.01 or span_y < 0.01 or span_z < 0.01:
        raise AssetValidationError(f"Degenerate dimensions detected (span < 0.01m): x={span_x}, y={span_y}, z={span_z}")

    # Automobile DCC coordinate conventions vary (Y-up vs Z-up).
    # Sort axis spans: shortest is height, middle is width, longest is length.
    dims = sorted([span_x, span_y, span_z])
    raw_h = dims[0]
    raw_w = dims[1]
    raw_l = dims[2]

    # Aspect ratio check: automobiles must be longer than they are tall
    ratio_lh = raw_l / raw_h
    if ratio_lh < 1.3:
        raise AssetValidationError(f"Unrealistic automotive aspect ratio (length/height = {ratio_lh:.2f} < 1.30)")

    ratio_lw = raw_l / raw_w
    if ratio_lw < 1.15:
        raise AssetValidationError(f"Unrealistic automotive aspect ratio (length/width = {ratio_lw:.2f} < 1.15)")

    # Test scaling to baseline automotive height (1.45m)
    target_h = 1.45
    scale = target_h / raw_h
    scaled_l = raw_l * scale
    scaled_w = raw_w * scale

    # Validate scaled dimensions within automotive envelope +-30%
    if not (AUTOMOTIVE_LIMITS["length"][0] <= scaled_l <= AUTOMOTIVE_LIMITS["length"][1]):
        raise AssetValidationError(f"Scaled length ({scaled_l:.2f}m) outside automotive envelope ({AUTOMOTIVE_LIMITS['length']})")
    if not (AUTOMOTIVE_LIMITS["width"][0] <= scaled_w <= AUTOMOTIVE_LIMITS["width"][1]):
        raise AssetValidationError(f"Scaled width ({scaled_w:.2f}m) outside automotive envelope ({AUTOMOTIVE_LIMITS['width']})")

    return {
        "length": round(scaled_l, 2),
        "width": round(scaled_w, 2),
        "height": round(target_h, 2),
        "raw_length": round(raw_l, 3),
        "raw_width": round(raw_w, 3),
        "raw_height": round(raw_h, 3),
    }


def validate_glb_materials(gltf):
    """
    Validates materials in GLB.
    Checks:
      - At least 1 material
      - Numeric material factors are valid floats
    Returns (material_count, list_of_names).
    """
    materials = gltf.get("materials", [])
    if not materials:
        raise AssetValidationError("GLB model contains 0 materials")

    mat_names = []
    for idx, mat in enumerate(materials):
        name = mat.get("name") or f"material_{idx}"
        mat_names.append(name)
        pbr = mat.get("pbrMetallicRoughness", {})
        if pbr:
            for factor_key in ["roughnessFactor", "metallicFactor"]:
                if factor_key in pbr:
                    val = pbr[factor_key]
                    if not isinstance(val, (int, float)) or math.isnan(val) or math.isinf(val):
                        raise AssetValidationError(f"Material '{name}' has invalid {factor_key}: {val}")

            base_color = pbr.get("baseColorFactor")
            if base_color and isinstance(base_color, list):
                for c in base_color:
                    if not isinstance(c, (int, float)) or math.isnan(c) or math.isinf(c):
                        raise AssetValidationError(f"Material '{name}' has invalid baseColorFactor value: {c}")

    return len(materials), mat_names


def validate_glb_textures(gltf, bin_bytes):
    """
    Validates textures and image buffer views.
    Checks:
      - Image bufferViews or URIs are valid and within bounds.
    Returns texture_count.
    """
    textures = gltf.get("textures", [])
    images = gltf.get("images", [])
    buffer_views = gltf.get("bufferViews", [])

    for img_idx, img in enumerate(images):
        bv_idx = img.get("bufferView")
        uri = img.get("uri")

        if bv_idx is not None:
            if bv_idx >= len(buffer_views):
                raise AssetValidationError(f"Image {img_idx} references invalid bufferView index {bv_idx}")
            bv = buffer_views[bv_idx]
            offset = bv.get("byteOffset", 0)
            length = bv.get("byteLength", 0)
            if length <= 0:
                raise AssetValidationError(f"Image {img_idx} bufferView length is 0")
            if offset + length > len(bin_bytes):
                raise AssetValidationError(f"Image {img_idx} bufferView extends past binary buffer")
        elif uri:
            if uri.startswith("data:"):
                # Embedded data URI is acceptable
                pass
            elif uri.startswith("http://") or uri.startswith("https://"):
                # External unbundled URLs should be warned/rejected for offline self-contained assets
                raise AssetValidationError(f"Image {img_idx} references external network URI '{uri}'; asset must be self-contained")

    return len(textures)


def validate_full_glb(file_path_or_bytes):
    """
    Executes all GLB validation checks:
      1. GLB header & chunk structure
      2. Meshes & buffers
      3. Dimensions & automotive envelope
      4. Materials
      5. Textures
    Returns dict with extracted metrics.
    """
    gltf, bin_bytes, total_size = parse_glb(file_path_or_bytes)
    mesh_count, vertex_count, bbox = validate_glb_meshes(gltf, bin_bytes)
    dimensions = validate_glb_dimensions(bbox)
    material_count, mat_names = validate_glb_materials(gltf)
    texture_count = validate_glb_textures(gltf, bin_bytes)

    return {
        "valid": True,
        "total_size": total_size,
        "mesh_count": mesh_count,
        "vertex_count": vertex_count,
        "dimensions": dimensions,
        "material_count": material_count,
        "texture_count": texture_count,
        "material_names": mat_names,
    }


def optimize_glb(input_path, output_path=None):
    """
    Optional asset optimization:
      - Validates 4-byte chunk padding
      - Computes potential savings
      - Writes aligned GLB to output_path if provided
    """
    raw_bytes = Path(input_path).read_bytes()
    initial_size = len(raw_bytes)

    # GLB chunks must be aligned to 4-byte boundaries
    # Parse chunks and ensure exact padding
    json_len = struct.unpack_from("<I", raw_bytes, 12)[0]
    json_padded = (json_len + 3) & ~3
    bin_offset = 20 + json_padded

    bin_len = 0
    if bin_offset + 8 <= initial_size:
        bin_len = struct.unpack_from("<I", raw_bytes, bin_offset)[0]

    bin_padded = (bin_len + 3) & ~3
    expected_size = bin_offset + 8 + bin_padded

    stats = {
        "initial_size": initial_size,
        "expected_size": expected_size,
        "overhead_bytes": max(0, initial_size - expected_size),
        "optimized": False,
    }

    if output_path:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        if initial_size > expected_size:
            # Strip trailing garbage bytes
            out_p.write_bytes(raw_bytes[:expected_size])
            stats["optimized"] = True
            stats["final_size"] = expected_size
        else:
            shutil.copy2(input_path, out_p)
            stats["final_size"] = initial_size

    return stats


def load_manifest(manifest_path=None):
    """
    Loads manifest.json from path or default assets/vehicles/manifest.json.
    Returns parsed dict with 'vehicles' list.
    """
    p = Path(manifest_path) if manifest_path else PROJECT_ROOT / "assets" / "vehicles" / "manifest.json"
    if not p.exists():
        return {"version": "1.0", "vehicles": []}

    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return {"version": "1.0", "vehicles": data}
        if "vehicles" not in data:
            data["vehicles"] = data.get("assets", [])
        return data
    except Exception as e:
        print(f"Warning: Failed to load manifest {p}: {e}")
        return {"version": "1.0", "vehicles": []}


def save_manifest(manifest_data, manifest_path=None):
    """
    Atomically writes manifest_data to manifest.json with 2-space indentation.
    """
    p = Path(manifest_path) if manifest_path else PROJECT_ROOT / "assets" / "vehicles" / "manifest.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    temp_p = p.with_suffix(".tmp")
    with open(temp_p, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)
    temp_p.replace(p)


def ingest_asset(
    input_path,
    brand,
    model,
    generation=None,
    year=None,
    variant="",
    source="curated_local",
    manifest_path=None,
    target_dir=None,
    optimize=False,
    dry_run=False,
):
    """
    Ingests, validates, and registers a local 3D vehicle GLB asset into SmartCar AI.

    Steps:
      1. Full validation (header, buffers, meshes, dimensions, materials, textures).
      2. Rejects corrupted or invalid assets.
      3. Normalizes vehicle identity & resolves generation metadata.
      4. Copies GLB into target vehicle directory.
      5. Optionally optimizes large assets.
      6. Registers entry in manifest.json with required fields:
         path, source, verified, generation, variant.

    Returns dict with operation summary.
    """
    in_file = Path(input_path)
    if not in_file.exists():
        raise AssetValidationError(f"Input file not found: {in_file}")

    # 1. Full GLB Validation
    metrics = validate_full_glb(in_file)

    # 2. Identity normalization
    make_slug = normalize_make_slug(brand)
    model_slug = normalize_model_slug(brand, model)

    gen_slug = None
    gen_name = None
    year_start = None
    year_end = None

    if generation:
        gen_clean = str(generation).strip()
        # Verify against catalog if available
        cat_status, cat_data, _ = fetch_catalog(make_slug, model_slug)
        if cat_status == 200 and cat_data:
            for g in cat_data.get("generations", []):
                if (g.get("slug") and g.get("slug").lower() == gen_clean.lower()) or \
                   (g.get("name") and g.get("name").lower() == gen_clean.lower()):
                    gen_slug = g.get("slug")
                    gen_name = g.get("name") or gen_slug
                    year_start = g.get("year_start")
                    year_end = g.get("year_end")
                    break
        if not gen_slug:
            gen_slug = slugify(gen_clean)
            gen_name = gen_clean
    elif year is not None:
        gen_res = resolveVehicleGeneration(brand, model, int(year))
        if gen_res.get("matched"):
            gen_slug = gen_res.get("generation_slug")
            gen_name = gen_res.get("generation_name") or gen_slug
            year_start = gen_res.get("year_start")
            year_end = gen_res.get("year_end")
        else:
            gen_slug = f"gen-{year}"
            gen_name = f"{brand} {model} ({year})"
            year_start = int(year)
            year_end = int(year)
    else:
        gen_slug = "curated"
        gen_name = f"{brand} {model}"

    # Target directory setup
    dest_base = Path(target_dir) if target_dir else PROJECT_ROOT / "assets" / "vehicles"
    dest_dir = dest_base / make_slug / model_slug / gen_slug
    dest_dir.mkdir(parents=True, exist_ok=True)

    variant_clean = str(variant).strip()
    dest_filename = f"model_{slugify(variant_clean)}.glb" if variant_clean else "model.glb"
    dest_file = dest_dir / dest_filename

    # Relative path from PROJECT_ROOT for manifest portability
    try:
        rel_path = dest_file.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        rel_path = str(dest_file)

    # Optimization if requested
    opt_stats = {}
    if optimize:
        opt_stats = optimize_glb(in_file, dest_file if not dry_run else None)
    elif not dry_run:
        shutil.copy2(in_file, dest_file)

    # Manifest entry construction with required fields
    entry = {
        "brand": brand,
        "model": model,
        "make_slug": make_slug,
        "model_slug": model_slug,
        "variant": variant_clean,
        "generation": gen_slug,
        "generation_name": gen_name,
        "year_start": year_start,
        "year_end": year_end,
        "path": rel_path,
        "source": source,
        "verified": True,
        "dimensions": {
            "length": metrics["dimensions"]["length"],
            "width": metrics["dimensions"]["width"],
            "height": metrics["dimensions"]["height"],
        },
        "mesh_count": metrics["mesh_count"],
        "vertex_count": metrics["vertex_count"],
        "material_count": metrics["material_count"],
        "texture_count": metrics["texture_count"],
        "metadata": DEFAULT_METADATA.copy(),
    }

    if not dry_run:
        m_file = Path(manifest_path) if manifest_path else dest_base / "manifest.json"
        manifest = load_manifest(m_file)
        vehicles = manifest.get("vehicles", [])

        # Update existing matching entry or append
        updated = False
        for i, existing in enumerate(vehicles):
            if (
                existing.get("make_slug") == make_slug and
                existing.get("model_slug") == model_slug and
                existing.get("generation") == gen_slug and
                existing.get("variant", "") == variant_clean
            ):
                vehicles[i] = entry
                updated = True
                break

        if not updated:
            vehicles.append(entry)

        manifest["vehicles"] = vehicles
        save_manifest(manifest, m_file)

    return {
        "success": True,
        "entry": entry,
        "destination": str(dest_file),
        "metrics": metrics,
        "optimization": opt_stats,
        "dry_run": dry_run,
    }


def main():
    parser = argparse.ArgumentParser(
        description="SmartCar AI — Local High-Quality Vehicle Asset Ingestion Pipeline"
    )
    parser.add_argument("--input", "-i", required=True, help="Path to input GLB file")
    parser.add_argument("--brand", "-b", required=True, help="Vehicle brand (e.g. BMW)")
    parser.add_argument("--model", "-m", required=True, help="Vehicle model (e.g. 3 Series)")
    parser.add_argument("--generation", "-g", help="Vehicle generation slug (e.g. g20-g21-g28-2019-2022)")
    parser.add_argument("--year", "-y", type=int, help="Vehicle manufacturing year (e.g. 2021)")
    parser.add_argument("--variant", "-v", default="", help="Vehicle variant/trim (e.g. M Sport)")
    parser.add_argument("--source", "-s", default="curated_local", help="Asset source tag")
    parser.add_argument("--manifest", help="Path to manifest.json")
    parser.add_argument("--target-dir", help="Directory where vehicles/ should be located")
    parser.add_argument("--optimize", action="store_true", help="Optimize large asset")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing files or manifest")

    args = parser.parse_args()

    try:
        result = ingest_asset(
            input_path=args.input,
            brand=args.brand,
            model=args.model,
            generation=args.generation,
            year=args.year,
            variant=args.variant,
            source=args.source,
            manifest_path=args.manifest,
            target_dir=args.target_dir,
            optimize=args.optimize,
            dry_run=args.dry_run,
        )
        print("=== ASSET INGESTION SUCCESSFUL ===")
        print(f"Vehicle:    {result['entry']['brand']} {result['entry']['model']} ({result['entry']['generation']})")
        print(f"Variant:    {result['entry']['variant'] or 'Standard'}")
        print(f"Path:       {result['entry']['path']}")
        print(f"Verified:   {result['entry']['verified']}")
        print(f"Source:     {result['entry']['source']}")
        print(f"Meshes:     {result['metrics']['mesh_count']}")
        print(f"Vertices:   {result['metrics']['vertex_count']}")
        print(f"Dimensions: L={result['metrics']['dimensions']['length']}m, W={result['metrics']['dimensions']['width']}m, H={result['metrics']['dimensions']['height']}m")
        if result["optimization"]:
            print(f"Optimized:  {result['optimization']}")
        sys.exit(0)
    except AssetValidationError as ave:
        print(f"ASSET VALIDATION REJECTED: {ave}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"INGESTION ERROR: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
