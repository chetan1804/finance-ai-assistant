import argparse
import json
from pathlib import Path

from src.evaluation.performance import performance_gate, run_load_test


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run a concurrent HTTP load test with explicit quality gates."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--endpoint", default="/ready")
    parser.add_argument("--token")
    parser.add_argument("--requests", type=int, default=200)
    parser.add_argument("--concurrency", type=int, default=20)
    parser.add_argument("--timeout-seconds", type=float, default=5)
    parser.add_argument("--max-p95-ms", type=float, default=500)
    parser.add_argument("--min-rps", type=float, default=20)
    parser.add_argument("--max-error-rate", type=float, default=0)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main():
    args = parse_args()
    if args.requests < 1 or args.concurrency < 1:
        raise SystemExit("requests and concurrency must be positive")
    if args.concurrency > args.requests:
        raise SystemExit("concurrency must not exceed requests")
    report = run_load_test(
        args.base_url,
        args.endpoint,
        request_count=args.requests,
        concurrency=args.concurrency,
        token=args.token,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps(report, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    failures = performance_gate(
        report,
        max_p95_ms=args.max_p95_ms,
        min_rps=args.min_rps,
        max_error_rate=args.max_error_rate,
    )
    if failures:
        for failure in failures:
            print(f"PERFORMANCE GATE FAILED: {failure}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
