from pathlib import Path

from scripts.evaluate_finance_agent import (
    create_evaluation_service,
    run_evaluation,
)
from src.evaluation.finance_agent_evaluator import (
    FinanceAgentEvaluator,
    load_evaluation_cases,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = (
    PROJECT_ROOT / "data" / "evaluation" / "finance_agent_cases.json"
)


def test_offline_evaluation_queries_are_exact(tmp_path):
    service, user_id = create_evaluation_service(tmp_path / "evaluation.db")
    cases = load_evaluation_cases(CASES_PATH)

    report = run_evaluation(cases, service, user_id, live=False)

    assert report["mode"] == "offline"
    assert report["summary"]["case_count"] == 8
    assert report["summary"]["query_accuracy"] == 1.0
    assert report["summary"]["context_accuracy"] is None
    assert report["summary"]["grounding_accuracy"] is None


def test_evaluator_detects_routing_and_grounding_failures(tmp_path):
    service, user_id = create_evaluation_service(tmp_path / "evaluation.db")
    evaluator = FinanceAgentEvaluator(service, user_id)
    case = load_evaluation_cases(CASES_PATH)[0]

    result = evaluator.evaluate_case(
        case,
        {
            "intent": "income",
            "category": None,
            "start_date": "2026-07-01",
            "end_date": "2026-07-31",
        },
        response_text="Your amount was ₹50,000.",
    )

    assert result["context_correct"] is False
    assert result["context_fields"]["intent"] is False
    assert result["query_correct"] is False
    assert result["grounding_correct"] is False


def test_evaluator_accepts_case_insensitive_categories(tmp_path):
    service, user_id = create_evaluation_service(tmp_path / "evaluation.db")
    evaluator = FinanceAgentEvaluator(service, user_id)
    case = load_evaluation_cases(CASES_PATH)[2]

    result = evaluator.evaluate_case(
        case,
        {
            **case["expected_context"],
            "category": "Food",
        },
        response_text="You spent ₹800 on food.",
    )

    assert result["context_correct"] is True
    assert result["query_correct"] is True
    assert result["grounding_correct"] is True
