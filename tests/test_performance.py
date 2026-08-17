from src.evaluation.performance import performance_gate, percentile, summarize_samples


def test_percentile_uses_nearest_rank():
    assert percentile([10, 20, 30, 40, 50], 0.50) == 30
    assert percentile([10, 20, 30, 40, 50], 0.95) == 50
    assert percentile([], 0.95) == 0


def test_performance_summary_and_gate():
    report = summarize_samples(
        [(10, 200), (20, 200), (30, 200), (40, 500)],
        duration_seconds=0.1,
    )

    assert report["requests_per_second"] == 40
    assert report["error_rate"] == 0.25
    assert performance_gate(
        report,
        max_p95_ms=35,
        min_rps=50,
        max_error_rate=0,
    ) == [
        "p95 latency 40.0ms exceeds 35.0ms",
        "throughput 40.0 rps is below 50.0 rps",
        "error rate 25.00% exceeds 0.00%",
    ]


def test_healthy_performance_report_passes_gate():
    report = summarize_samples([(12, 200)] * 100, duration_seconds=1)

    assert performance_gate(
        report,
        max_p95_ms=100,
        min_rps=50,
        max_error_rate=0,
    ) == []
