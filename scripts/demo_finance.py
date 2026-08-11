from src.database.db import initialize_database
from src.services.finance_service import FinanceService


def main():

    # Make sure database exists
    initialize_database()

    finance = FinanceService()

    # ------------------------------------------------
    # 1. Create User
    # ------------------------------------------------

    user_id = finance.create_user(
        name="Demo User",
        email="demo@example.com",
        currency="INR"
    )

    print(f"User created: {user_id}")

    # ------------------------------------------------
    # 2. Create Account
    # ------------------------------------------------

    account_id = finance.create_account(
        user_id=user_id,
        name="Main Bank Account",
        account_type="bank",
        institution="Demo Bank",
        balance=0
    )

    print(f"Account created: {account_id}")

    # ------------------------------------------------
    # 3. Create Categories
    # ------------------------------------------------

    salary_category = finance.create_category(
        user_id=user_id,
        name="Salary",
        category_type="income"
    )

    food_category = finance.create_category(
        user_id=user_id,
        name="Food",
        category_type="expense"
    )

    transport_category = finance.create_category(
        user_id=user_id,
        name="Transport",
        category_type="expense"
    )

    shopping_category = finance.create_category(
        user_id=user_id,
        name="Shopping",
        category_type="expense"
    )

    # ------------------------------------------------
    # 4. Add Income
    # ------------------------------------------------

    finance.add_transaction(
        user_id=user_id,
        account_id=account_id,
        category_id=salary_category,
        transaction_type="income",
        amount=80000,
        description="Monthly salary",
        merchant="Company"
    )

    # ------------------------------------------------
    # 5. Add Expenses
    # ------------------------------------------------

    finance.add_transaction(
        user_id=user_id,
        account_id=account_id,
        category_id=food_category,
        transaction_type="expense",
        amount=8000,
        description="Monthly food expenses"
    )

    finance.add_transaction(
        user_id=user_id,
        account_id=account_id,
        category_id=transport_category,
        transaction_type="expense",
        amount=5000,
        description="Fuel and transportation"
    )

    finance.add_transaction(
        user_id=user_id,
        account_id=account_id,
        category_id=shopping_category,
        transaction_type="expense",
        amount=7000,
        description="Online shopping"
    )

    # ------------------------------------------------
    # 6. Print Financial Summary
    # ------------------------------------------------

    income = finance.get_total_income(user_id)
    expenses = finance.get_total_expenses(user_id)
    savings = finance.get_savings(user_id)

    print("\n-----------------------------")
    print("FINANCIAL SUMMARY")
    print("-----------------------------")

    print(f"Total Income   : ₹{income:,.2f}")
    print(f"Total Expenses : ₹{expenses:,.2f}")
    print(f"Savings        : ₹{savings:,.2f}")

    # ------------------------------------------------
    # 7. Category Analysis
    # ------------------------------------------------

    print("\n-----------------------------")
    print("EXPENSES BY CATEGORY")
    print("-----------------------------")

    categories = finance.get_expenses_by_category(user_id)

    for row in categories:

        print(
            f"{row['category']:15} "
            f"₹{row['total']:,.2f}"
        )

    # ------------------------------------------------
    # 8. Transactions
    # ------------------------------------------------

    print("\n-----------------------------")
    print("TRANSACTIONS")
    print("-----------------------------")

    transactions = finance.get_transactions(user_id)

    for transaction in transactions:

        print(
            f"{transaction['transaction_date']} | "
            f"{transaction['transaction_type']:8} | "
            f"₹{transaction['amount']:,.2f} | "
            f"{transaction['category']} | "
            f"{transaction['description']}"
        )


if __name__ == "__main__":
    main()