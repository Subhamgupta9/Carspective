# ============================================================
# SMARTCAR AI — PHASE 2: VEHICLE ASSET RESOLVER
# vehicle_asset_resolver.py — Deterministic Vehicle Identity Resolution
# ============================================================
#
# Resolution Priority (5-tier):
#   1. exact_local         — Exact local asset on disk (curated or Studio HD)
#   2. verified_local      — Same-generation verified GLB in local cache
#   3. api_sanitized       — CarImages API match, downloaded, sanitized & validated
#   4. generation_fallback — API returned fallback generation (identity preserved)
#   5. unavailable         — No valid asset available
#
# Rules:
#   1. Exact local asset has highest priority.
#   2. Verified same-generation local asset is second.
#   3. Validated CarImages API asset is third.
#   4. Generation fallback is allowed only when identity remains correct.
#   5. Otherwise return unavailable.
#   6. NEVER silently substitute an unrelated vehicle.
#   7. NEVER use fuzzy "contains" generation matching.
#   8. Validate downloaded GLBs.
#   9. Reject invalid GLBs.
#   10. Never expose CarImages API credentials.
#   11. Frontend must receive only safe local/project URLs.
# ============================================================

import os
import re
import json
import copy
from collections import OrderedDict
from pathlib import Path

try:
    from app.carimages_service import (
        normalize_make_slug,
        normalize_model_slug,
        slugify,
        fetch_catalog,
        resolveVehicleGeneration,
        fetch_vehicle_model,
        get_cached_or_download_glb,
        CACHE_DIR,
    )
except ImportError:
    from carimages_service import (
        normalize_make_slug,
        normalize_model_slug,
        slugify,
        fetch_catalog,
        resolveVehicleGeneration,
        fetch_vehicle_model,
        get_cached_or_download_glb,
        CACHE_DIR,
    )

# Root asset directory for curated local models
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "vehicles"

# Studio HD registry — high-fidelity showcase assets
STUDIO_HD_REGISTRY = {
    ("porsche", "911"): {
        "path": Path(__file__).resolve().parent / "static" / "models" / "generic_car.glb",
        "generation_slug": "992-2019-2025",
        "generation_name": "Porsche 911 Carrera 4S (Studio HD)",
        "year_start": 2019,
        "year_end": 2025,
        "metadata": {
            "targetHeight": 1.55,
            "baseHeading": -1.5707963267948966,
            "groundOffset": 0.18915,
            "cameraDistance": 7.2,
            "cameraTargetHeight": 0.75,
            "cameraTargetZ": 3.2,
        },
    }
}

# Default metadata for standard vehicle models
DEFAULT_METADATA = {
    "targetHeight": 1.50,
    "baseHeading": -1.5707963267948966,
    "groundOffset": 0.0,
}

# Minimum valid GLB file size (bytes)
MIN_GLB_SIZE = 1000

# GLB magic bytes
GLB_MAGIC = b"glTF"


def validate_glb(filepath):
    """
    Validates a GLB file:
      1. File exists
      2. Size >= MIN_GLB_SIZE
      3. Starts with GLB magic bytes b"glTF"
    Returns (is_valid, reason)
    """
    if not filepath:
        return False, "path_none"
    p = Path(filepath)
    if not p.exists():
        return False, "file_not_found"
    try:
        size = p.stat().st_size
    except Exception as e:
        return False, f"stat_error: {e}"
    if size < MIN_GLB_SIZE:
        return False, f"file_too_small ({size} bytes < {MIN_GLB_SIZE})"
    try:
        with open(p, "rb") as f:
            magic = f.read(4)
        if magic != GLB_MAGIC:
            return False, f"invalid_magic_bytes ({magic!r} != {GLB_MAGIC!r})"
    except Exception as e:
        return False, f"read_error: {e}"
    return True, "valid"


class VehicleAssetResolver:
    """
    Deterministic Vehicle Asset Resolution Engine.

    Resolves (brand, model, year, generation) to the best available
    3D GLB asset using a strict 5-tier priority system.
    """

    def __init__(self, assets_dir=None, cache_dir=None, manifest_path=None, max_cache_size=256, **kwargs):
        self.assets_dir = Path(assets_dir) if assets_dir else ASSETS_DIR
        self.cache_dir = Path(cache_dir) if cache_dir else CACHE_DIR
        self.manifest_path = Path(manifest_path) if manifest_path else self.assets_dir / "manifest.json"
        self._manifest_cache = None
        self._manifest_mtime = None
        self._resolution_cache = OrderedDict()
        self._max_cache_size = kwargs.get("cache_size", max_cache_size)
        self._cache_hits = 0
        self._cache_misses = 0

    def get_cache_stats(self):
        """Returns resolution cache telemetry."""
        return {
            "cache_size": len(self._resolution_cache),
            "max_cache_size": self._max_cache_size,
            "max_size": self._max_cache_size,
            "hits": self._cache_hits,
            "misses": self._cache_misses
        }

    def clear_cache(self):
        """Flushes in-memory resolution cache."""
        self._resolution_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0

    def resolve(self, brand, model, year=None, generation=None, variant=None):
        """
        Main resolution method with thread-safe LRU caching.
        """
        cache_key = (
            str(brand or "").strip().lower(),
            str(model or "").strip().lower(),
            int(year) if year is not None and str(year).isdigit() else str(year or ""),
            str(generation or "").strip().lower(),
            str(variant or "").strip().lower()
        )

        if cache_key in self._resolution_cache:
            self._cache_hits += 1
            self._resolution_cache.move_to_end(cache_key)
            return copy.deepcopy(self._resolution_cache[cache_key])

        self._cache_misses += 1
        result = self._resolve_uncached(brand, model, year=year, generation=generation, variant=variant)

        if result.get("status") in ("exact_local", "verified_local"):
            self._resolution_cache[cache_key] = copy.deepcopy(result)
            self._resolution_cache.move_to_end(cache_key)
            if len(self._resolution_cache) > self._max_cache_size:
                self._resolution_cache.popitem(last=False)
        elif result.get("status") == "api_sanitized":
            cached_item = copy.deepcopy(result)
            cached_item["status"] = "verified_local"
            self._resolution_cache[cache_key] = cached_item
            self._resolution_cache.move_to_end(cache_key)
            if len(self._resolution_cache) > self._max_cache_size:
                self._resolution_cache.popitem(last=False)

        return result

    def _resolve_uncached(self, brand, model, year=None, generation=None, variant=None):
        """
        Internal uncached resolution logic.
        """
        warnings = []

        # 0. Basic parameter validation
        if not brand or not model:
            return self._unavailable(
                brand, model, year, variant, warnings,
                reason="Missing required parameters: brand and model"
            )

        make_slug = normalize_make_slug(brand)
        model_slug = normalize_model_slug(brand, model)

        year_int = None
        if year is not None:
            try:
                year_int = int(year)
            except (ValueError, TypeError):
                warnings.append(f"Invalid year value: {year}")

        # ─── TIER 1: Exact Local Manifest Match (Highest Priority) ───
        manifest_exact = self._find_manifest_match(
            brand, model, year_int, make_slug, model_slug, generation, variant, warnings
        )
        if manifest_exact:
            return manifest_exact

        # Fallback to curated assets directory (for non-manifested legacy assets)
        local_exact = self._find_exact_local_asset(
            brand, model, year_int, make_slug, model_slug, generation, variant, warnings
        )
        if local_exact:
            return local_exact

        # Check Studio HD Showcase registry
        studio_key = (make_slug, model_slug)
        if studio_key in STUDIO_HD_REGISTRY:
            entry = STUDIO_HD_REGISTRY[studio_key]
            studio_path = entry["path"]
            valid, reason = validate_glb(studio_path)
            if valid:
                return {
                    "status": "exact_local",
                    "path": "/static/models/generic_car.glb",
                    "metadata": entry["metadata"],
                    "warnings": warnings,
                    "vehicle": {
                        "brand": brand,
                        "model": model,
                        "year": year_int or 2021,
                        "variant": variant or "",
                    },
                    "asset": {
                        "source": "studio_hd",
                        "make_slug": make_slug,
                        "model_slug": model_slug,
                        "generation_slug": entry["generation_slug"],
                        "generation_name": entry["generation_name"],
                        "year_start": entry["year_start"],
                        "year_end": entry["year_end"],
                        "match_level": "EXACT_VARIANT",
                        "fallback": False,
                    },
                }
            else:
                warnings.append(f"Studio HD asset rejected: {reason}")

        # Year is required for generation resolution if no generation provided
        if not generation and year_int is None:
            return self._unavailable(
                brand, model, year_int, variant, warnings,
                reason="Year is required when generation is not specified",
                make_slug=make_slug, model_slug=model_slug
            )

        # ─── Generation Resolution (Strict, No Fuzzy Matching) ───
        gen_slug = None
        gen_name = None
        y_start = None
        y_end = None

        if generation:
            # Explicit generation requested — validate against make/model catalog if available
            gen_clean = str(generation).strip()
            cat_status, cat_data, _ = fetch_catalog(make_slug, model_slug)
            if cat_status == 200 and cat_data:
                catalog_gens = cat_data.get("generations", [])
                # Rule 7: Strict exact matching on slug or name, NEVER fuzzy substring / "contains"
                matched_g = None
                for g in catalog_gens:
                    g_slug = str(g.get("slug") or "").strip()
                    g_name = str(g.get("name") or "").strip()
                    if (g_slug and g_slug.lower() == gen_clean.lower()) or (g_name and g_name.lower() == gen_clean.lower()):
                        matched_g = g
                        break
                
                if matched_g:
                    gen_slug = matched_g.get("slug")
                    gen_name = matched_g.get("name") or gen_slug
                    y_start = matched_g.get("year_start")
                    y_end = matched_g.get("year_end")
                else:
                    # Explicit generation does not belong to this model!
                    # Rule 6: NEVER silently substitute an unrelated vehicle or wrong generation
                    warnings.append(
                        f"Generation '{generation}' does not match any valid generation for {brand} {model}"
                    )
                    return self._unavailable(
                        brand, model, year_int, variant, warnings,
                        reason=f"Wrong generation: '{generation}' is invalid for {brand} {model}",
                        make_slug=make_slug, model_slug=model_slug
                    )
            else:
                # Catalog not reachable — accept explicit slug directly but do not fuzzy match
                gen_slug = slugify(gen_clean)
                gen_name = gen_clean

        elif year_int is not None:
            # Deterministic lookup by year via canonical resolver
            gen_res = resolveVehicleGeneration(brand, model, year_int)
            if gen_res.get("matched"):
                gen_slug = gen_res.get("generation_slug")
                gen_name = gen_res.get("generation_name") or gen_slug
                y_start = gen_res.get("year_start")
                y_end = gen_res.get("year_end")
            else:
                warnings.append(f"No generation found for {brand} {model} ({year_int})")
                return self._unavailable(
                    brand, model, year_int, variant, warnings,
                    reason=f"No matching generation for {brand} {model} ({year_int})",
                    make_slug=make_slug, model_slug=model_slug
                )

        if not gen_slug:
            return self._unavailable(
                brand, model, year_int, variant, warnings,
                reason="Could not determine vehicle generation",
                make_slug=make_slug, model_slug=model_slug
            )

        # ─── TIER 2: Verified Local Cache (Same Generation) ───
        cache_file = self.cache_dir / f"{make_slug}_{model_slug}_{gen_slug}.glb"
        if cache_file.exists():
            valid, reason = validate_glb(cache_file)
            if valid:
                local_url = f"/api/vehicle-model/{make_slug}/{model_slug}/{gen_slug}"
                return {
                    "status": "verified_local",
                    "path": local_url,
                    "metadata": DEFAULT_METADATA.copy(),
                    "warnings": warnings,
                    "vehicle": {
                        "brand": brand,
                        "model": model,
                        "year": year_int,
                        "variant": variant or "",
                    },
                    "asset": {
                        "source": "local_cache",
                        "make_slug": make_slug,
                        "model_slug": model_slug,
                        "generation_slug": gen_slug,
                        "generation_name": gen_name,
                        "year_start": y_start,
                        "year_end": y_end,
                        "match_level": "GENERATION_MATCH",
                        "fallback": False,
                    },
                }
            else:
                # Rule 9: Reject invalid GLBs
                warnings.append(f"Cached asset failed validation: {reason}")

        # ─── TIER 3 & 4: Validated CarImages API Asset ───
        mod_status, mod_data, mod_err = fetch_vehicle_model(make_slug, model_slug, gen_slug)
        if mod_status == 200 and mod_data:
            model_info = mod_data.get("model", {})
            remote_glb_url = model_info.get("glb")
            is_fallback = bool(model_info.get("fallback", False))

            if remote_glb_url:
                cached_path = get_cached_or_download_glb(
                    make_slug, model_slug, gen_slug, remote_glb_url
                )
                if cached_path:
                    # Rule 8: Validate downloaded GLB
                    valid, reason = validate_glb(cached_path)
                    if valid:
                        local_url = f"/api/vehicle-model/{make_slug}/{model_slug}/{gen_slug}"
                        status = "generation_fallback" if is_fallback else "api_sanitized"
                        match_level = "GENERATION_FALLBACK" if is_fallback else "GENERATION_MATCH"
                        if is_fallback:
                            warnings.append(
                                f"API returned fallback generation for {brand} {model}"
                            )
                        return {
                            "status": status,
                            "path": local_url,
                            "metadata": DEFAULT_METADATA.copy(),
                            "warnings": warnings,
                            "vehicle": {
                                "brand": brand,
                                "model": model,
                                "year": year_int,
                                "variant": variant or "",
                            },
                            "asset": {
                                "source": "carimagesapi",
                                "make_slug": make_slug,
                                "model_slug": model_slug,
                                "generation_slug": gen_slug,
                                "generation_name": gen_name,
                                "year_start": y_start,
                                "year_end": y_end,
                                "match_level": match_level,
                                "fallback": is_fallback,
                            },
                        }
                    else:
                        warnings.append(f"Downloaded GLB failed validation: {reason}")
            else:
                warnings.append("API returned 3D model metadata but no GLB URL")
        else:
            if mod_err:
                warnings.append(f"CarImages API error: {mod_err}")

        # ─── TIER 5: Unavailable ───
        return self._unavailable(
            brand, model, year_int, variant, warnings,
            reason="No verified asset available locally or from API",
            gen_slug=gen_slug, gen_name=gen_name,
            make_slug=make_slug, model_slug=model_slug,
            y_start=y_start, y_end=y_end
        )

    def _find_exact_local_asset(self, brand, model, year, make_slug, model_slug,
                                generation, variant, warnings):
        """
        Searches assets/vehicles/ for an exact local GLB file.
        Checks:
          1. assets/vehicles/{Brand} {Model} {Year}/*.glb
          2. assets/vehicles/{make_slug}/{model_slug}/{generation}/*.glb
          3. assets/vehicles/{make_slug}/{model_slug}/{year}/*.glb
        Validates with validate_glb(). Rejects invalid files.
        """
        if not self.assets_dir.exists():
            return None

        candidate_dirs = []

        # Benchmark directory pattern: e.g. "BMW 3 Series 2021"
        if year:
            candidate_dirs.append(self.assets_dir / f"{brand} {model} {year}")
            # Also with normalized make
            candidate_dirs.append(self.assets_dir / f"{make_slug} {model_slug} {year}")

        # Nested directory patterns
        if generation:
            candidate_dirs.append(self.assets_dir / make_slug / model_slug / slugify(generation))
        if year:
            candidate_dirs.append(self.assets_dir / make_slug / model_slug / str(year))

        candidate_dirs.append(self.assets_dir / make_slug / model_slug)

        for c_dir in candidate_dirs:
            if c_dir.is_dir():
                # Check for variant-specific or general model.glb files
                glb_files = []
                if variant:
                    v_slug = slugify(variant)
                    glb_files.extend(list(c_dir.glob(f"*{v_slug}*.glb")))
                glb_files.extend(list(c_dir.glob("*.glb")))

                for glb_file in glb_files:
                    valid, reason = validate_glb(glb_file)
                    if valid:
                        gen_val = generation or (str(year) if year else "local")
                        return {
                            "status": "exact_local",
                            "path": f"/api/vehicle-model/{make_slug}/{model_slug}/{gen_val}",
                            "metadata": DEFAULT_METADATA.copy(),
                            "warnings": warnings,
                            "vehicle": {
                                "brand": brand,
                                "model": model,
                                "year": year,
                                "variant": variant or "",
                            },
                            "asset": {
                                "source": "exact_local",
                                "make_slug": make_slug,
                                "model_slug": model_slug,
                                "generation_slug": gen_val,
                                "generation_name": f"{brand} {model} (Curated Local)",
                                "match_level": "EXACT_VARIANT",
                                "fallback": False,
                                "local_path": str(glb_file),
                            },
                        }
                    else:
                        warnings.append(f"Local asset at {glb_file.name} invalid: {reason}")

        return None

    def _unavailable(self, brand, model, year, variant, warnings,
                     reason=None, gen_slug=None, gen_name=None,
                     make_slug=None, model_slug=None, y_start=None, y_end=None):
        if reason and reason not in warnings:
            warnings.append(reason)
        return {
            "status": "unavailable",
            "path": None,
            "metadata": {},
            "warnings": warnings,
            "vehicle": {
                "brand": brand or "",
                "model": model or "",
                "year": year,
                "variant": variant or "",
            },
            "asset": {
                "source": "none",
                "make_slug": make_slug or "",
                "model_slug": model_slug or "",
                "generation_slug": gen_slug,
                "generation_name": gen_name,
                "year_start": y_start,
                "year_end": y_end,
                "match_level": "GENERATION_UNAVAILABLE",
                "fallback": False,
            },
        }

    def load_manifest(self, force_reload=False):
        """
        Loads assets/vehicles/manifest.json.
        Caches manifest in memory with mtime invalidation.
        Returns list of manifest vehicle entry dicts.
        """
        if not self.manifest_path or not self.manifest_path.exists():
            return []

        try:
            mtime = self.manifest_path.stat().st_mtime
            if not force_reload and self._manifest_cache is not None and self._manifest_mtime == mtime:
                return self._manifest_cache

            with open(self.manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                entries = data
            elif isinstance(data, dict):
                entries = data.get("vehicles") or data.get("assets") or []
            else:
                entries = []

            self._manifest_cache = entries
            self._manifest_mtime = mtime
            return entries
        except Exception:
            return []

    def _find_manifest_match(self, brand, model, year, make_slug, model_slug,
                             generation, variant, warnings):
        """
        Tier 1 priority: Checks assets/vehicles/manifest.json for a verified match.
        Matches by make/model and variant/generation/year.
        Validates the physical GLB file on disk before returning exact_local.
        """
        entries = self.load_manifest()
        if not entries:
            return None

        # Filter by make and model
        candidates = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if not entry.get("verified", False):
                continue

            e_make = normalize_make_slug(entry.get("brand") or entry.get("make_slug") or "")
            e_model = normalize_model_slug(
                entry.get("brand") or entry.get("make_slug") or "",
                entry.get("model") or entry.get("model_slug") or ""
            )
            if e_make == make_slug and e_model == model_slug:
                candidates.append(entry)

        if not candidates:
            return None

        best_entry = None

        # 1. If variant requested, prioritize exact variant match
        if variant:
            v_clean = str(variant).strip().lower()
            for cand in candidates:
                cand_v = str(cand.get("variant") or "").strip().lower()
                if cand_v and cand_v == v_clean:
                    if self._entry_matches_generation_or_year(cand, generation, year, brand, model):
                        best_entry = cand
                        break

        # 2. Check generation match if generation requested
        if generation:
            gen_clean = str(generation).strip().lower()
            for cand in candidates:
                cand_gen = str(cand.get("generation") or "").strip().lower()
                cand_gen_name = str(cand.get("generation_name") or "").strip().lower()
                if cand_gen == gen_clean or cand_gen_name == gen_clean or slugify(cand_gen) == slugify(gen_clean):
                    best_entry = cand
                    break
            # If an explicit generation was requested, never fall back to year matching
            if not best_entry:
                return None

        # 3. Check year match if year requested (and no generation override)
        if not best_entry and year is not None:
            for cand in candidates:
                y_start = cand.get("year_start")
                y_end = cand.get("year_end")
                if y_start is not None and y_end is not None:
                    if y_start <= year <= y_end:
                        best_entry = cand
                        break
                elif cand.get("generation"):
                    gen_res = resolveVehicleGeneration(brand, model, year)
                    if gen_res.get("matched") and gen_res.get("generation_slug") == cand.get("generation"):
                        best_entry = cand
                        break

        # 4. If neither generation nor year was restricted, and exactly 1 candidate exists
        if not best_entry and not generation and year is None and len(candidates) == 1:
            best_entry = candidates[0]

        if not best_entry:
            return None

        # Validate physical file on disk
        entry_path = best_entry.get("path")
        if not entry_path:
            warnings.append("Manifest entry lacks 'path' field")
            return None

        disk_path = self._resolve_manifest_disk_path(entry_path)
        valid, reason = validate_glb(disk_path)
        if not valid:
            warnings.append(f"Manifest asset rejected ({reason}): {entry_path}")
            return None

        safe_url = self._get_safe_frontend_url(best_entry, disk_path, make_slug, model_slug)
        gen_val = best_entry.get("generation") or (str(year) if year else "local")
        gen_name_val = best_entry.get("generation_name") or gen_val
        is_studio_hd = best_entry.get("source") == "studio_hd"
        match_level = "EXACT_VARIANT" if (variant or is_studio_hd) else "EXACT_MANIFEST"

        return {
            "status": "exact_local",
            "path": safe_url,
            "metadata": best_entry.get("metadata", DEFAULT_METADATA).copy(),
            "warnings": warnings,
            "vehicle": {
                "brand": best_entry.get("brand") or brand,
                "model": best_entry.get("model") or model,
                "year": year or best_entry.get("year_start"),
                "variant": variant or best_entry.get("variant", ""),
            },
            "asset": {
                "source": best_entry.get("source", "curated_local"),
                "make_slug": make_slug,
                "model_slug": model_slug,
                "generation_slug": gen_val,
                "generation_name": gen_name_val,
                "year_start": best_entry.get("year_start"),
                "year_end": best_entry.get("year_end"),
                "variant": best_entry.get("variant", ""),
                "match_level": match_level,
                "fallback": False,
                "manifest_path": str(entry_path),
                "verified": True,
            },
        }

    def _entry_matches_generation_or_year(self, cand, generation, year, brand, model):
        """Helper to test whether a candidate manifest entry matches generation or year."""
        if generation:
            cand_gen = str(cand.get("generation") or "").strip().lower()
            cand_name = str(cand.get("generation_name") or "").strip().lower()
            gen_clean = str(generation).strip().lower()
            return cand_gen == gen_clean or cand_name == gen_clean or slugify(cand_gen) == slugify(gen_clean)
        if year is not None:
            y_start = cand.get("year_start")
            y_end = cand.get("year_end")
            if y_start is not None and y_end is not None:
                return y_start <= year <= y_end
            gen_res = resolveVehicleGeneration(brand, model, year)
            if gen_res.get("matched"):
                return gen_res.get("generation_slug") == cand.get("generation")
        return True

    def _resolve_manifest_disk_path(self, entry_path):
        """Resolves manifest entry path to an absolute Path on the filesystem."""
        p = Path(entry_path)
        if p.is_absolute() and p.exists():
            return p

        # Check relative to project root
        root_cand = Path(__file__).resolve().parent.parent / entry_path
        if root_cand.exists():
            return root_cand

        # Check relative to assets_dir
        assets_cand = self.assets_dir / entry_path
        if assets_cand.exists():
            return assets_cand

        return root_cand

    def _get_safe_frontend_url(self, entry, disk_path, make_slug, model_slug):
        """Constructs safe frontend URL for serving the 3D model."""
        # 1. If static asset inside app/static/
        static_dir = Path(__file__).resolve().parent / "static"
        try:
            rel = disk_path.resolve().relative_to(static_dir.resolve())
            return f"/static/{rel.as_posix()}"
        except (ValueError, RuntimeError):
            pass

        # 2. Curated asset served via streaming endpoint
        gen_val = entry.get("generation") or "curated"
        return f"/api/vehicle-model/{make_slug}/{model_slug}/{gen_val}"

