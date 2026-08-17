import math
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def percentile(values, quantile):
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(quantile * len(ordered)) - 1)
    return ordered[index]


def summarize_samples(samples, duration_seconds):
    latencies = [sample[0] for sample in samples]
    successes = sum(1 for _, status_code in samples if 200 <= status_code < 400)
    total = len(samples)
    return {
        "requests": total,
        "successes": successes,
        "errors": total - successes,
        "error_rate": (total - successes) / total if total else 1.0,
        "requests_per_second": total / duration_seconds if duration_seconds else 0.0,
        "latency_ms": {
            "p50": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
            "p99": percentile(latencies, 0.99),
            "max": max(latencies, default=0.0),
        },
        "duration_seconds": duration_seconds,
    }


def _request(url, token, timeout_seconds):
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    started_at = time.perf_counter()
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            response.read()
            status_code = response.status
    except HTTPError as error:
        status_code = error.code
    except (TimeoutError, URLError):
        status_code = 0
    latency_ms = (time.perf_counter() - started_at) * 1000
    return latency_ms, status_code


def run_load_test(
    base_url,
    endpoint,
    *,
    request_count,
    concurrency,
    token=None,
    timeout_seconds=5,
    warmup_requests=5,
):
    url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    for _ in range(warmup_requests):
        _request(url, token, timeout_seconds)
    started_at = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        samples = list(
            executor.map(
                lambda _index: _request(url, token, timeout_seconds),
                range(request_count),
            )
        )
    duration = time.perf_counter() - started_at
    return summarize_samples(samples, duration)


def performance_gate(report, *, max_p95_ms, min_rps, max_error_rate):
    failures = []
    if report["latency_ms"]["p95"] > max_p95_ms:
        failures.append(
            f"p95 latency {report['latency_ms']['p95']:.1f}ms exceeds {max_p95_ms:.1f}ms"
        )
    if report["requests_per_second"] < min_rps:
        failures.append(
            f"throughput {report['requests_per_second']:.1f} rps is below {min_rps:.1f} rps"
        )
    if report["error_rate"] > max_error_rate:
        failures.append(
            f"error rate {report['error_rate']:.2%} exceeds {max_error_rate:.2%}"
        )
    return failures
