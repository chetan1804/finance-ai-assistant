from src.tools.finance_tools import (
    get_total_income,
    get_total_expenses,
    get_total_savings,
    get_category_expenses,
)


def test_total_income():

    result = get_total_income.invoke({})

    assert isinstance(
        result,
        (int, float)
    )


def test_total_expenses():

    result = get_total_expenses.invoke({})

    assert isinstance(
        result,
        (int, float)
    )


def test_total_savings():

    result = get_total_savings.invoke({})

    assert isinstance(
        result,
        (int, float)
    )


def test_category_expenses():

    result = get_category_expenses.invoke({
        "category": "Food"
    })

    assert isinstance(
        result,
        (int, float)
    )