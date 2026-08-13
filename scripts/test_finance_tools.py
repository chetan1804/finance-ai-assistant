from src.tools.finance_tools import (
    get_total_income,
    get_total_expenses,
    get_total_savings,
    get_category_expenses,
    get_largest_expense,
    get_merchant_expenses,
    get_transaction_count,
)


def main():

    print(
        "Total income:",
        get_total_income.invoke({})
    )

    print(
        "Total expenses:",
        get_total_expenses.invoke({})
    )

    print(
        "Total savings:",
        get_total_savings.invoke({})
    )

    print(
        "Food expenses:",
        get_category_expenses.invoke({
            "category": "Food"
        })
    )

    print(
        "Largest expense:",
        get_largest_expense.invoke({})
    )

    print(
        "Amazon expenses:",
        get_merchant_expenses.invoke({
            "merchant": "Amazon"
        })
    )

    print(
        "Transaction count:",
        get_transaction_count.invoke({})
    )


if __name__ == "__main__":
    main()