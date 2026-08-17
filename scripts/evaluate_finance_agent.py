import argparse
import json
import tempfile
from pathlib import Path

from src.database.db import initialize_database
from src.database.finance_service import FinanceService
from src.evaluation.finance_agent_evaluator import (
    FinanceAgentEvaluator,
    load_evaluation_cases,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CASES = (
    PROJECT_ROOT / "data" / "evaluation" / "finance_agent_cases.json"
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate finance-agent routing, queries, and grounding."
    )
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Call the configured LLM to evaluate routing and responses.",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.8,
        help="Minimum acceptable value for every measured metric.",
    )
    return parser.parse_args()


def create_evaluation_service(database_path):
    """Create a repeatable database whose values match the benchmark cases."""
    initialize_database(database_path)
    service = FinanceService(database_path)
    user_id = service.create_user("Evaluation User", "eval@example.com")
    account_id = service.create_account(user_id, "Evaluation Bank", "savings")
    food_id = service.create_category(user_id, "Food", "expense")

    transactions = [
        ("income", 50000, "Salary", "2026-07-01"),
        ("expense", 1200, "Groceries", "2026-07-10"),
        ("expense", 800, "Dinner", "2026-06-02"),
    ]
    for transaction_type, amount, description, transaction_date in transactions:
        service.add_transaction(
            user_id=user_id,
            account_id=account_id,
            category_id=food_id,
            transaction_type=transaction_type,
            amount=amount,
            description=description,
            transaction_date=transaction_date,
        )

    return service, user_id


def _live_context_and_response(case, service, user_id):
    from langchain_core.messages import HumanMessage

    from src.agents.finance_agent import extract_context, generate_response
    from src.agents.query import execute_finance_query

    messages = [HumanMessage(content=text) for text in case["messages"]]
    context = extract_context({"messages": messages, "user_id": user_id})
    result = execute_finance_query(service, user_id, context)
    response = generate_response(
        {
            "messages": messages,
            "user_id": user_id,
            **context,
            "finance_result": result,
            "preferences": service.get_user_preferences(user_id),
        }
    )["messages"][-1].content
    return context, response


def run_evaluation(cases, service, user_id, live=False):
    evaluator = FinanceAgentEvaluator(service, user_id)
    results = []

    for case in cases:
        if live:
            actual_context, response = _live_context_and_response(
                case,
                service,
                user_id,
            )
        else:
            actual_context = dict(case["expected_context"])
            response = None

        results.append(
            evaluator.evaluate_case(
                case,
                actual_context,
                response_text=response,
                context_evaluated=live,
            )
        )

    return {
        "mode": "live" if live else "offline",
        "summary": evaluator.summarize(results),
        "cases": results,
    }


def print_report(report):
    summary = report["summary"]
    print(f"\nFinance Agent Evaluation ({report['mode']})")
    print("=" * 45)
    print(f"Cases                  : {summary['case_count']}")

    for label, key in (
        ("Context accuracy", "context_accuracy"),
        ("Context field accuracy", "context_field_accuracy"),
        ("Query accuracy", "query_accuracy"),
        ("Grounding accuracy", "grounding_accuracy"),
        ("Safety accuracy", "safety_accuracy"),
    ):
        value = summary[key]
        display = "not measured" if value is None else f"{value:.1%}"
        print(f"{label:<23}: {display}")

    failures = [
        result
        for result in report["cases"]
        if result["query_correct"] is False
        or result["context_correct"] is False
        or result["grounding_correct"] is False
        or result["safety_correct"] is False
    ]
    if failures:
        print("\nFailed cases:")
        for result in failures:
            print(f"- {result['name']}")


def main():
    args = parse_args()
    cases = load_evaluation_cases(args.cases)

    with tempfile.TemporaryDirectory(prefix="finance-agent-eval-") as temp_dir:
        service, user_id = create_evaluation_service(
            Path(temp_dir) / "evaluation.db"
        )
        report = run_evaluation(cases, service, user_id, live=args.live)

    print_report(report)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"\nReport written to {args.output}")

    measured_scores = [
        score
        for key, score in report["summary"].items()
        if key != "case_count" and score is not None
    ]
    if any(score < args.min_score for score in measured_scores):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
