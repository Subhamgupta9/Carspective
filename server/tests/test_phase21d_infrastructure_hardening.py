"""
CARspective — Phase 21D: Production Infrastructure Hardening Verification Suite

Validates the architecture, syntax, security constraints, and configuration semantics
of the production multi-container topology, NGINX gateway, and Prometheus monitoring.
"""

import re
from pathlib import Path
import yaml
import pytest
from server.infrastructure.observability.metrics import metrics_collector


def test_docker_compose_prod_topology_and_security():
    """Validates docker-compose.prod.yml syntax, services, dependencies, network isolation, and secret guards."""
    compose_path = Path("docker-compose.prod.yml")
    assert compose_path.exists(), "docker-compose.prod.yml must exist!"

    raw_text = compose_path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw_text)
    assert "services" in data, "Compose file must define services"
    services = data["services"]

    required_services = ["db", "migrator", "api", "gateway"]
    for svc in required_services:
        assert svc in services, f"Missing required service: {svc}"

    # Verify dependency DAG
    assert services["migrator"]["depends_on"]["db"]["condition"] == "service_healthy"
    assert services["api"]["depends_on"]["migrator"]["condition"] == "service_completed_successfully"
    assert services["api"]["depends_on"]["db"]["condition"] == "service_healthy"
    assert services["gateway"]["depends_on"]["api"]["condition"] == "service_healthy"

    # Verify network isolation: api port 5001 is NOT published to host
    api_svc = services["api"]
    assert "ports" not in api_svc, "API service must not publish ports directly to host"
    assert "5001" in str(api_svc.get("expose", [])), "API service must expose port 5001 internally"

    # Verify TRUSTED_PROXIES is configured for ProxyFix
    api_env = api_svc.get("environment", {})
    if isinstance(api_env, list):
        env_dict = dict(item.split("=", 1) for item in api_env if "=" in item)
    else:
        env_dict = api_env
    assert str(env_dict.get("TRUSTED_PROXIES")) == "1", "TRUSTED_PROXIES must be set to 1 for NGINX proxy"

    # Verify Gateway publishes 80/443
    gateway_ports = str(services["gateway"].get("ports", []))
    assert "80" in gateway_ports and "443" in gateway_ports, "Gateway must publish 80 and 443"

    # Verify Gateway mounts TLS certificates read-only
    gateway_vols = str(services["gateway"].get("volumes", []))
    assert "/etc/nginx/certs:ro" in gateway_vols, "Gateway must mount /etc/nginx/certs read-only (:ro)"

    # Verify mandatory secret interpolation syntax (${VAR:?...}) prevents default secret leaks
    assert "${POSTGRES_PASSWORD:?" in raw_text, "POSTGRES_PASSWORD must use mandatory substitution syntax"
    assert "${SECRET_KEY:?" in raw_text, "SECRET_KEY must use mandatory substitution syntax"
    assert "${ADMIN_API_KEY:?" in raw_text, "ADMIN_API_KEY must use mandatory substitution syntax"
    assert "${TLS_CERT_DIR:?" in raw_text, "TLS_CERT_DIR must use mandatory substitution syntax"

    # Verify Prometheus monitoring profile and secret file mount
    if "prometheus" in services:
        prom_svc = services["prometheus"]
        assert "monitoring" in prom_svc.get("profiles", []), "Prometheus must belong to monitoring profile"
        prom_vols = str(prom_svc.get("volumes", []))
        assert "/etc/prometheus/secrets/admin_api_key:ro" in prom_vols, "Prometheus must mount secret file read-only"
        assert "${PROMETHEUS_ADMIN_KEY_FILE:?" in raw_text, "PROMETHEUS_ADMIN_KEY_FILE must use mandatory substitution"


def test_nginx_configurations_integrity():
    """Validates NGINX main and site configurations for keepalive, rate-limiting, fail-closed SSL/TLS, and error formats."""
    main_conf = Path("docker/nginx/nginx.conf")
    site_conf = Path("docker/nginx/conf.d/carspective.conf")
    nginx_dockerfile = Path("docker/nginx/Dockerfile")

    assert main_conf.exists(), "docker/nginx/nginx.conf must exist!"
    assert site_conf.exists(), "docker/nginx/conf.d/carspective.conf must exist!"
    assert nginx_dockerfile.exists(), "docker/nginx/Dockerfile must exist!"

    main_text = main_conf.read_text(encoding="utf-8")
    site_text = site_conf.read_text(encoding="utf-8")
    dockerfile_text = nginx_dockerfile.read_text(encoding="utf-8")

    # Main conf checks
    assert "json_analytics" in main_text, "NGINX must configure structured JSON logging"
    assert "limit_req_zone" in main_text, "NGINX must configure rate limiting zones"
    assert "client_max_body_size 5M" in main_text, "Payload size must be capped at 5M"
    assert "gzip on" in main_text, "Gzip compression must be enabled"

    # Site conf checks
    assert "upstream carspective_backend" in site_text, "Must define upstream carspective_backend"
    assert "keepalive 32;" in site_text, "Must configure upstream keepalive pool to eliminate socket queue stalls"
    assert "proxy_http_version 1.1;" in site_text, "Must use HTTP 1.1 for upstream keepalive"
    assert "limit_req zone=api_valuation" in site_text, "Valuation route must have dedicated rate limiting"
    assert "error_page 429 = @rate_limited;" in site_text, "Must handle 429 with RFC 7807 JSON"
    assert "application/problem+json" in site_text, "Must return problem+json mimetype"
    assert "alias /usr/share/nginx/html/assets/;" in site_text, "Must offload static assets directly"

    # TLS / SSL fail-closed checks
    assert "listen 443 ssl" in site_text, "Must listen on port 443 with SSL enabled"
    assert "ssl_certificate /etc/nginx/certs/carspective.crt;" in site_text, "Must reference production carspective.crt"
    assert "ssl_certificate_key /etc/nginx/certs/carspective.key;" in site_text, "Must reference production carspective.key"
    assert "ssl_protocols TLSv1.2 TLSv1.3;" in site_text, "Must enforce TLS 1.2 and 1.3 only"

    # Strict fail-closed verification: NO self-signed certificates in image or configuration
    assert "selfsigned" not in site_text, "NGINX configuration must never reference fallback self-signed certificates"
    assert "selfsigned" not in dockerfile_text, "NGINX Dockerfile must never bake in self-signed certificates"
    assert "openssl req" not in dockerfile_text, "NGINX Dockerfile must not generate baked-in TLS keys"


def test_prometheus_monitoring_specifications():
    """Validates Prometheus scraper configuration and alerting rules against real metrics telemetry."""
    prom_path = Path("monitoring/prometheus.yml")
    alerts_path = Path("monitoring/alerts.yml")

    assert prom_path.exists(), "monitoring/prometheus.yml must exist!"
    assert alerts_path.exists(), "monitoring/alerts.yml must exist!"

    prom_data = yaml.safe_load(prom_path.read_text(encoding="utf-8"))
    alerts_data = yaml.safe_load(alerts_path.read_text(encoding="utf-8"))

    # Prometheus scraper checks
    scrape_jobs = {job["job_name"]: job for job in prom_data.get("scrape_configs", [])}
    assert "carspective-api" in scrape_jobs, "Must define carspective-api scraper job"
    api_job = scrape_jobs["carspective-api"]

    # Verify secret file authentication (remediates MED-01)
    assert api_job.get("bearer_token_file") == "/etc/prometheus/secrets/admin_api_key", \
        "Scraper must read bearer token from mounted secret file"
    assert "bearer_token" not in api_job, "Scraper must not use unexpanded bearer_token environment string"
    assert api_job.get("metrics_path") == "/metrics", "Scraper must target /metrics"

    # Alerts checks
    groups = alerts_data.get("groups", [])
    assert len(groups) > 0, "Must define alert groups"
    alert_rules = groups[0].get("rules", [])
    alert_names = {rule["alert"] for rule in alert_rules}

    required_alerts = [
        "CarSpectiveServiceDown",
        "CarSpectiveDatabaseFailuresSpike",
        "CarSpectiveHigh5xxErrorRate",
        "CarSpectiveHighLatency",
        "CarSpectiveClientErrorSpike",
    ]
    for alert in required_alerts:
        assert alert in alert_names, f"Missing critical alert rule: {alert}"

    # Verify that all application metrics referenced in alert expressions exist in Prometheus text export
    prom_text = metrics_collector.get_prometheus_text()
    for rule in alert_rules:
        expr = rule.get("expr", "")
        app_metric_matches = re.findall(r"\b(carspective_[a-zA-Z0-9_]+)\b", expr)
        for metric_name in app_metric_matches:
            assert metric_name in prom_text, f"Alert rule '{rule['alert']}' references unknown metric '{metric_name}'!"


def test_docker_entrypoint_script_semantics():
    """Validates the structure, operational branching, and credential isolation of docker-entrypoint.sh."""
    entrypoint_path = Path("docker-entrypoint.sh")
    assert entrypoint_path.exists(), "docker-entrypoint.sh must exist!"

    content = entrypoint_path.read_text(encoding="utf-8")
    assert content.startswith("#!/bin/sh"), "Entrypoint must specify #!/bin/sh shebang"
    assert "set -e" in content, "Entrypoint must fail fast on errors (set -e)"
    assert "DATABASE_WAIT" in content, "Entrypoint must support DATABASE_WAIT readiness loop"
    assert "AUTO_MIGRATE" in content, "Entrypoint must support AUTO_MIGRATE schema migration flag"
    assert 'if [ "$#" -gt 0 ]; then' in content, "Entrypoint must support custom container command passthrough"
    assert "gunicorn" in content, "Entrypoint must fallback to production Gunicorn invocation"
    assert "server.wsgi:app" in content, "Entrypoint Gunicorn command must reference server.wsgi:app"

    # Invariant: DATABASE_URL must NOT be shell-interpolated into python -c command arguments (remediates HIGH-01)
    assert "url = '${DATABASE_URL}'" not in content, "DATABASE_URL must not be interpolated into python argv"
    assert 'url = "${DATABASE_URL}"' not in content, "DATABASE_URL must not be interpolated into python argv"
    assert "os.environ.get('DATABASE_URL'" in content, "Python command must read DATABASE_URL safely from os.environ"
