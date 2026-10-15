"""
CARspective — Lightweight Operational Metrics & Service Telemetry
Provides thread-safe in-memory metrics collection with strictly bounded label
cardinality, latency histogram buckets, uptime calculation, and Prometheus text export.
Operates purely with the Python standard library with zero external dependencies.
"""

import time
import threading
from typing import Dict, Any, Tuple, Optional, List


# Standard Prometheus-compatible duration buckets (in seconds)
LATENCY_BUCKETS: Tuple[float, ...] = (
    0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0
)

# Allowed HTTP methods to bound method cardinality
ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"}


def normalize_method(method: Optional[str]) -> str:
    """Normalizes HTTP method to a strict bounded set."""
    if not method:
        return "UNKNOWN"
    upper = method.strip().upper()
    return upper if upper in ALLOWED_METHODS else "OTHER"


def normalize_status_class(status_code: int) -> str:
    """Maps HTTP status code to its 1xx-5xx class."""
    if 100 <= status_code < 600:
        return f"{status_code // 100}xx"
    return "unknown"


def normalize_route(url_rule: Optional[str], path: Optional[str]) -> str:
    """
    Normalizes request route to prevent cardinality explosion:
    - Uses the Flask route template (e.g., '/api/v1/vehicles/<slug>')
    - Groups static asset paths into 'static_asset'
    - Falls back to 'unmatched' for 404s
    Never uses raw query strings or unmapped path segments.
    """
    if url_rule:
        return url_rule

    clean_path = (path or "").strip()
    if clean_path.startswith("/assets/") or clean_path.endswith((".js", ".css", ".png", ".jpg", ".svg", ".ico", ".woff", ".woff2")):
        return "static_asset"

    return "unmatched"


class MetricsCollector:
    """
    Thread-safe operational telemetry collector for a single application instance.
    Maintains bounded-cardinality counters, duration histograms, and failure metrics.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._start_time: float = time.time()
        self._requests_total: int = 0
        self._requests_by_labels: Dict[Tuple[str, str, str], int] = {}
        self._http_5xx_total: int = 0
        self._database_failures_total: int = 0
        self._duration_bucket_counts: Dict[float, int] = {b: 0 for b in LATENCY_BUCKETS}
        self._duration_sum: float = 0.0
        self._duration_count: int = 0

    def record_request(
        self,
        method: str,
        route: Optional[str],
        status_code: int,
        duration_seconds: float
    ) -> None:
        """
        Records a completed HTTP request with bounded cardinality labels.
        """
        norm_method = normalize_method(method)
        norm_route = route if route else "unmatched"
        norm_status_class = normalize_status_class(status_code)
        label_key = (norm_method, norm_route, norm_status_class)

        with self._lock:
            self._requests_total += 1
            self._requests_by_labels[label_key] = self._requests_by_labels.get(label_key, 0) + 1

            if status_code >= 500:
                self._http_5xx_total += 1

            # Duration tracking
            self._duration_count += 1
            self._duration_sum += duration_seconds
            for b in LATENCY_BUCKETS:
                if duration_seconds <= b:
                    self._duration_bucket_counts[b] += 1

    def record_database_failure(self) -> None:
        """
        Increments the database connectivity or readiness check failure counter.
        """
        with self._lock:
            self._database_failures_total += 1

    def get_uptime_seconds(self) -> float:
        """Returns application uptime in seconds."""
        return max(0.0, time.time() - self._start_time)

    def get_summary(self) -> Dict[str, Any]:
        """
        Returns a sanitized JSON-serializable operational summary.
        Does NOT expose environment variables, filesystem paths, database URLs,
        or internal system credentials.
        """
        with self._lock:
            uptime = self.get_uptime_seconds()
            avg_duration_ms = (
                round((self._duration_sum / self._duration_count) * 1000, 2)
                if self._duration_count > 0 else 0.0
            )

            # Format partitioned requests
            partitioned: List[Dict[str, Any]] = [
                {
                    "method": m,
                    "route": r,
                    "status_class": s,
                    "count": count
                }
                for (m, r, s), count in sorted(self._requests_by_labels.items())
            ]

            # Format latency histogram
            histogram_buckets: Dict[str, int] = {
                f"le_{b}s": count for b, count in sorted(self._duration_bucket_counts.items())
            }

            return {
                "service": "carspective-api",
                "uptime_seconds": round(uptime, 2),
                "total_requests": self._requests_total,
                "http_5xx_total": self._http_5xx_total,
                "database_failures_total": self._database_failures_total,
                "latency_summary": {
                    "total_count": self._duration_count,
                    "total_duration_seconds": round(self._duration_sum, 4),
                    "avg_duration_ms": avg_duration_ms,
                    "histogram_buckets": histogram_buckets
                },
                "requests_by_route": partitioned
            }

    def get_prometheus_text(self) -> str:
        """
        Outputs metrics in standard Prometheus exposition text format.
        """
        with self._lock:
            lines: List[str] = [
                "# HELP carspective_process_uptime_seconds Application process uptime in seconds",
                "# TYPE carspective_process_uptime_seconds gauge",
                f"carspective_process_uptime_seconds {round(self.get_uptime_seconds(), 2)}",
                "",
                "# HELP carspective_http_requests_total Total HTTP requests handled",
                "# TYPE carspective_http_requests_total counter",
                f"carspective_http_requests_total {self._requests_total}",
                "",
                "# HELP carspective_http_5xx_total Total HTTP 5xx responses generated",
                "# TYPE carspective_http_5xx_total counter",
                f"carspective_http_5xx_total {self._http_5xx_total}",
                "",
                "# HELP carspective_database_failures_total Total database connectivity and readiness failures",
                "# TYPE carspective_database_failures_total counter",
                f"carspective_database_failures_total {self._database_failures_total}",
                "",
                "# HELP carspective_http_requests_partitioned HTTP requests by method, route, and status class",
                "# TYPE carspective_http_requests_partitioned counter",
            ]

            for (m, r, s), count in sorted(self._requests_by_labels.items()):
                # Escape quotes in route label if any
                clean_r = r.replace('"', '\\"')
                lines.append(f'carspective_http_requests_partitioned{{method="{m}",route="{clean_r}",status_class="{s}"}} {count}')

            lines.extend([
                "",
                "# HELP carspective_http_request_duration_seconds Request duration histogram in seconds",
                "# TYPE carspective_http_request_duration_seconds histogram",
            ])
            for b in sorted(self._duration_bucket_counts.keys()):
                lines.append(f'carspective_http_request_duration_seconds_bucket{{le="{b}"}} {self._duration_bucket_counts[b]}')
            lines.append(f'carspective_http_request_duration_seconds_bucket{{le="+Inf"}} {self._duration_count}')
            lines.append(f'carspective_http_request_duration_seconds_sum {round(self._duration_sum, 6)}')
            lines.append(f'carspective_http_request_duration_seconds_count {self._duration_count}')
            lines.append("")

            return "\n".join(lines)

    def reset(self) -> None:
        """Resets all metrics state (used for clean testing isolation)."""
        with self._lock:
            self._start_time = time.time()
            self._requests_total = 0
            self._requests_by_labels.clear()
            self._http_5xx_total = 0
            self._database_failures_total = 0
            self._duration_bucket_counts = {b: 0 for b in LATENCY_BUCKETS}
            self._duration_sum = 0.0
            self._duration_count = 0


# Global process singleton
metrics_collector = MetricsCollector()
