"""
CARspective — Server Application Factory
Initializes modular Flask application with database session scoping, blueprints,
request tracing, structured observability logging, RFC 7807 error handlers, and client serving.
"""

import os
import uuid
import time
import json
import logging
from flask import Flask, jsonify, request, g, send_from_directory, abort, Response
from server.config import settings
from server.infrastructure.database import ScopedSession, init_db
from server.infrastructure.observability import (
    setup_logging,
    validate_or_generate_request_id,
    metrics_collector,
    normalize_route,
)
from server.api.v1 import (
    taxonomy_bp,
    evidence_bp,
    valuation_bp,
    deal_bp,
    score_bp,
    recommendation_bp,
    comparison_bp,
    inspection_bp,
    assistant_bp,
    market_bp,
    ownership_bp,
    decision_bp,
    data_bp,
)

logger = setup_logging("carspective.server")

def create_app(test_config=None, validate_config=None) -> Flask:
    app = Flask(__name__)
    
    app.config["ENV"] = settings.ENV
    app.config["DEBUG"] = settings.DEBUG
    app.config["SECRET_KEY"] = settings.SECRET_KEY

    if test_config:
        app.config.update(test_config)

    # Structured application startup log
    logger.info(
        f'{{"event": "application_startup", "env": "{settings.ENV}", '
        f'"is_production": {json.dumps(settings.IS_PRODUCTION)}, "pid": {os.getpid()}}}'
    )

    # Validate production configuration fail-fast
    should_validate = validate_config if validate_config is not None else (
        settings.IS_PRODUCTION and not app.testing and not app.config.get("TESTING")
    )
    if should_validate:
        settings.validate_production_config()

    # Conditional reverse proxy support (RFC 7239 / X-Forwarded-*)
    if settings.TRUSTED_PROXIES > 0:
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(
            app.wsgi_app,
            x_for=settings.TRUSTED_PROXIES,
            x_proto=settings.TRUSTED_PROXIES,
            x_host=settings.TRUSTED_PROXIES,
            x_prefix=settings.TRUSTED_PROXIES,
        )

    # Initialize tables in non-production environments (dev/test)
    # In production, unreviewed automated DDL is prohibited; schema is managed via Alembic
    if not settings.IS_PRODUCTION or app.testing or app.config.get("TESTING"):
        init_db()

    # Register clean database connection pool disposal on process termination
    from server.infrastructure.database import dispose_engine
    import atexit
    if not getattr(app, "_engine_disposal_registered", False):
        def _on_shutdown():
            try:
                logger.info('{"event": "application_shutdown", "reason": "engine_disposal"}')
            except Exception:
                pass
            dispose_engine()

        atexit.register(_on_shutdown)
        app._engine_disposal_registered = True

    # Register API Blueprints
    app.register_blueprint(taxonomy_bp)
    app.register_blueprint(evidence_bp)
    app.register_blueprint(valuation_bp)
    app.register_blueprint(deal_bp)
    app.register_blueprint(score_bp)
    app.register_blueprint(recommendation_bp)
    app.register_blueprint(comparison_bp)
    app.register_blueprint(inspection_bp)
    app.register_blueprint(assistant_bp)
    app.register_blueprint(market_bp)
    app.register_blueprint(ownership_bp)
    app.register_blueprint(decision_bp)
    app.register_blueprint(data_bp)

    # Request Lifecycle: Request ID, CORS & Performance Tracing
    @app.before_request
    def before_request_trace():
        raw_req_id = request.headers.get("X-Request-ID")
        req_id = validate_or_generate_request_id(raw_req_id)
        g.request_id = req_id
        g.start_time = time.perf_counter()

        # Host header validation in production (DNS rebinding / host spoofing defense)
        if settings.IS_PRODUCTION and not app.testing and not app.config.get("TESTING"):
            raw_host = request.host
            host_without_port = raw_host.split(":")[0]
            if host_without_port not in settings.ALLOWED_HOSTS and raw_host not in settings.ALLOWED_HOSTS:
                logger.warning(
                    f'{{"event": "untrusted_host_blocked", "host": "{raw_host}", '
                    f'"remote_addr": "{request.remote_addr}", "request_id": "{req_id}"}}'
                )
                abort(400, description=f"Untrusted Host header: {host_without_port}")

        if request.method == "OPTIONS":
            response = app.make_default_options_response()
            origin = request.headers.get("Origin")
            if origin and (origin in settings.ALLOWED_ORIGINS or ("*" in settings.ALLOWED_ORIGINS and not settings.IS_PRODUCTION)):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Request-ID, X-Admin-Api-Key"
                response.headers["Access-Control-Max-Age"] = "86400"
                response.headers["Vary"] = "Origin"
            return response

    @app.after_request
    def after_request_trace(response):
        duration_s = max(0.0, time.perf_counter() - getattr(g, "start_time", time.perf_counter()))
        latency_ms = round(duration_s * 1000, 2)
        req_id = getattr(g, "request_id", "unknown")
        response.headers["X-Request-ID"] = req_id

        # CORS Response Headers (explicit origins, no wildcard in production)
        origin = request.headers.get("Origin")
        if origin and (origin in settings.ALLOWED_ORIGINS or ("*" in settings.ALLOWED_ORIGINS and not settings.IS_PRODUCTION)):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-Request-ID, X-Admin-Api-Key"
            response.headers["Access-Control-Max-Age"] = "86400"
            response.headers["Vary"] = "Origin"

        # Operational Metrics Recording (bounded cardinality)
        route_rule = request.url_rule.rule if request.url_rule else normalize_route(None, request.path)
        metrics_collector.record_request(
            method=request.method,
            route=route_rule,
            status_code=response.status_code,
            duration_seconds=duration_s
        )

        # Health Check Noise Suppression & Structured Observability Logging
        is_health_endpoint = request.path in ("/health", "/health/liveness", "/ready", "/health/readiness")
        if is_health_endpoint:
            if response.status_code == 200:
                logger.debug(
                    f'{{"event": "health_check_ok", "path": "{request.path}", "status": 200, '
                    f'"latency_ms": {latency_ms}, "request_id": "{req_id}"}}'
                )
            else:
                logger.warning(
                    f'{{"event": "health_check_failed", "path": "{request.path}", '
                    f'"status": {response.status_code}, "latency_ms": {latency_ms}, "request_id": "{req_id}"}}'
                )
        elif not app.testing and not request.path.startswith("/assets/") and not request.path.endswith((".js", ".css", ".png", ".jpg", ".svg", ".ico", ".woff", ".woff2")):
            log_payload = {
                "event": "request_completed",
                "request_id": req_id,
                "method": request.method,
                "route": route_rule,
                "path": request.path,
                "status": response.status_code,
                "latency_ms": latency_ms,
                "remote_addr": request.remote_addr
            }
            logger.info(json.dumps(log_payload))

        return response

    # Teardown database session after each request
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        ScopedSession.remove()

    # RFC 7807 Structured Error Handlers for API requests
    def format_rfc7807_error(status_code: int, title: str, detail: str, code: str = "ERROR"):
        req_id = getattr(g, "request_id", "unknown")
        return jsonify({
            "type": f"https://carspective.internal/errors/{code.lower()}",
            "title": title,
            "status": status_code,
            "detail": detail,
            "error_code": code,
            "request_id": req_id
        }), status_code

    @app.errorhandler(400)
    def handle_bad_request(e):
        if request.path.startswith("/api/"):
            return format_rfc7807_error(400, "Bad Request", str(e.description if hasattr(e, "description") else e), "INVALID_REQUEST")
        return e

    @app.errorhandler(404)
    def handle_not_found(e):
        if request.path.startswith("/api/"):
            return format_rfc7807_error(404, "Not Found", f"Resource at '{request.path}' was not found.", "RESOURCE_NOT_FOUND")
        return e

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        if request.path.startswith("/api/"):
            return format_rfc7807_error(405, "Method Not Allowed", f"Method '{request.method}' is not permitted for '{request.path}'.", "METHOD_NOT_ALLOWED")
        return e

    @app.errorhandler(500)
    def handle_server_error(e):
        req_id = getattr(g, "request_id", "unknown")
        error_summary = str(e).splitlines()[0][:200].replace('"', "'") if e else "Unknown error"
        logger.error(
            f'{{"event": "unhandled_exception", "request_id": "{req_id}", "error_type": "{type(e).__name__}", "error": "{error_summary}"}}',
            exc_info=True
        )
        if request.path.startswith("/api/"):
            return format_rfc7807_error(500, "Internal Server Error", "An internal error occurred while processing the request. Contact support with the request ID.", "INTERNAL_SERVER_ERROR")
        return e

    # Health & Operational Endpoints
    def check_liveness():
        req_id = getattr(g, "request_id", "unknown")
        return jsonify({
            "status": "UP",
            "service": "carspective-api",
            "request_id": req_id,
            "version": "1.2.0"
        }), 200

    @app.route("/health", methods=["GET"])
    def health_root():
        return check_liveness()

    @app.route("/health/liveness", methods=["GET"])
    def liveness():
        return check_liveness()

    def check_readiness():
        checks = {}
        is_ready = True
        
        # 1. Database check
        try:
            from sqlalchemy import text
            from server.infrastructure.database import engine
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            checks["database"] = "CONNECTED"
        except Exception as e:
            req_id = getattr(g, "request_id", "unknown")
            clean_err = str(e).replace('"', "'")
            metrics_collector.record_database_failure()
            logger.error(
                f'{{"event": "readiness_check_failed", "check": "database", "error": "{clean_err}", "request_id": "{req_id}"}}'
            )
            checks["database"] = "UNAVAILABLE"
            is_ready = False

        # 2. Model artifact integrity check
        model_joblib = os.path.join("models", "carspective_valuation_lgbm_v1.joblib")
        model_manifest = os.path.join("models", "carspective_valuation_lgbm_v1_manifest.json")
        if os.path.exists(model_joblib) and os.path.exists(model_manifest):
            checks["valuation_model"] = "VERIFIED"
        else:
            checks["valuation_model"] = "MISSING_ARTIFACTS"
            is_ready = False

        # 3. Taxonomy data availability
        try:
            from server.models.taxonomy import Manufacturer
            session = ScopedSession()
            count = session.query(Manufacturer).count()
            if count > 0:
                checks["taxonomy"] = f"READY ({count} manufacturers)"
            else:
                checks["taxonomy"] = "EMPTY"
                is_ready = False
        except Exception as e:
            req_id = getattr(g, "request_id", "unknown")
            clean_err = str(e).replace('"', "'")
            logger.error(
                f'{{"event": "readiness_check_failed", "check": "taxonomy", "error": "{clean_err}", "request_id": "{req_id}"}}'
            )
            checks["taxonomy"] = "UNAVAILABLE"
            is_ready = False

        status_code = 200 if is_ready else 503
        return jsonify({
            "status": "READY" if is_ready else "NOT_READY",
            "service": "carspective-api",
            "checks": checks,
            "request_id": getattr(g, "request_id", "unknown")
        }), status_code

    @app.route("/ready", methods=["GET"])
    def ready_root():
        return check_readiness()

    @app.route("/health/readiness", methods=["GET"])
    def readiness():
        return check_readiness()

    # Operational Telemetry & Metrics Endpoints
    def get_metrics_payload():
        req_id = getattr(g, "request_id", "unknown")
        # In production mode, administrative authorization is strictly enforced
        if settings.IS_PRODUCTION and not app.testing and not app.config.get("TESTING"):
            from server.utils.auth import extract_admin_key_from_request, verify_admin_api_key
            api_key = extract_admin_key_from_request(request)
            if not api_key or not verify_admin_api_key(api_key):
                logger.warning(
                    f'{{"event": "unauthorized_metrics_access", "path": "{request.path}", '
                    f'"remote_addr": "{request.remote_addr}", "request_id": "{req_id}"}}'
                )
                return format_rfc7807_error(
                    401,
                    "Unauthorized",
                    "Administrative authorization is required to access operational telemetry metrics.",
                    "UNAUTHORIZED"
                )

        format_param = request.args.get("format", "").strip().lower()
        accept_header = request.headers.get("Accept", "").lower()
        if format_param == "prometheus" or "text/plain" in accept_header:
            return Response(
                metrics_collector.get_prometheus_text(),
                mimetype="text/plain; version=0.0.4; charset=utf-8"
            )

        return jsonify(metrics_collector.get_summary()), 200

    @app.route("/metrics", methods=["GET"])
    def metrics_root():
        return get_metrics_payload()

    @app.route("/api/v1/metrics", methods=["GET"])
    def api_metrics():
        return get_metrics_payload()

    @app.route("/api/v1", methods=["GET"])
    def api_index():
        return jsonify({
            "service": "CARspective Intelligent Automotive Intelligence Platform API",
            "version": "v1.2",
            "status": "OPERATIONAL",
            "request_id": getattr(g, "request_id", "unknown"),
            "endpoints": {
                "taxonomy": "/api/v1/vehicles",
                "evidence": "/api/v1/evidence",
                "valuation": "/api/v1/valuation",
                "deal_analysis": "/api/v1/deal-analysis",
                "score": "/api/v1/score",
                "recommendation": "/api/v1/recommendation",
                "comparison": "/api/v1/compare",
                "inspection": "/api/v1/inspection",
                "assistant": "/api/v1/assistant",
                "decision": "/api/v1/decision",
                "metrics": "/api/v1/metrics"
            }
        }), 200

    # Modern Client Static Serving (Phase 9) with Strict Path Traversal Protection
    client_dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "client", "dist"))
    if os.path.isdir(client_dist_dir):
        @app.route("/", defaults={"path": ""})
        @app.route("/<path:path>")
        def serve_client(path):
            if path.startswith("api/") or path.startswith("health/") or path.startswith("ready"):
                abort(404)
            # Null byte & traversal sanitization
            if "\x00" in path or ".." in path:
                abort(400)
            
            clean_path = os.path.normpath(path).lstrip(r"\/").replace(os.sep, "/")
            target = os.path.abspath(os.path.join(client_dist_dir, clean_path))
            
            # Defense-in-depth: Ensure target stays strictly inside client_dist_dir
            if not target.startswith(client_dist_dir):
                abort(404)
                
            if clean_path and os.path.isfile(target):
                return send_from_directory(client_dist_dir, clean_path)
            return send_from_directory(client_dist_dir, "index.html")

    return app

if __name__ == "__main__":
    import sys
    if settings.IS_PRODUCTION:
        sys.stderr.write(
            "CRITICAL: Direct execution of server/app.py with the development server in production is prohibited.\n"
            "Use a production WSGI server (e.g. gunicorn or waitress) to serve the application.\n"
        )
        sys.exit(1)
    app = create_app()
    app.run(host="0.0.0.0", port=5001, debug=settings.DEBUG)
