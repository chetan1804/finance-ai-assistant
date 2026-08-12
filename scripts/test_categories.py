from src.services.category_service import CategoryService


def main():

    service = CategoryService()

    transactions = [
        ("Swiggy Food Order", "Swiggy"),
        ("Uber Ride", "Uber"),
        ("Amazon Purchase", "Amazon"),
        ("Electricity Bill", "MSEDCL"),
        ("Netflix Subscription", "Netflix"),
        ("Grocery Shopping", "DMart"),
    ]

    for description, merchant in transactions:

        category = service.categorize(
            description,
            merchant
        )

        print(
            f"{description:25} -> {category}"
        )


if __name__ == "__main__":
    main()