import csv
import random
from datetime import date, timedelta


CATEGORY_DATA = {

    "Food": [
        ("Swiggy Food Order", "Swiggy"),
        ("Zomato Order", "Zomato"),
        ("Restaurant Dinner", "Restaurant"),
        ("Restaurant Lunch", "Restaurant"),
        ("Cafe Coffee", "Cafe"),
        ("Grocery Shopping", "DMart"),
    ],

    "Transport": [
        ("Uber Ride", "Uber"),
        ("Ola Ride", "Ola"),
        ("Fuel Purchase", "HP Petrol Pump"),
        ("Petrol", "Indian Oil"),
        ("Bus Ticket", "Bus"),
        ("Train Ticket", "IRCTC"),
    ],

    "Shopping": [
        ("Amazon Purchase", "Amazon"),
        ("Flipkart Purchase", "Flipkart"),
        ("Clothing Purchase", "Shopping Mall"),
        ("Electronics Purchase", "Amazon"),
        ("Online Shopping", "Myntra"),
    ],

    "Bills": [
        ("Electricity Bill", "MSEDCL"),
        ("Mobile Bill", "Jio"),
        ("Internet Bill", "Jio"),
        ("Water Bill", "Municipal Corporation"),
        ("Gas Bill", "Gas Provider"),
    ],

    "Entertainment": [
        ("Netflix Subscription", "Netflix"),
        ("Spotify Subscription", "Spotify"),
        ("Movie Ticket", "PVR"),
        ("Movie Ticket", "INOX"),
    ],

    "Salary": [
        ("Monthly Salary", "ABC Company"),
        ("Salary Credit", "XYZ Company"),
        ("Freelance Payment", "Freelance Client"),
    ]
}


def random_amount(category):

    ranges = {

        "Food": (100, 3000),

        "Transport": (100, 5000),

        "Shopping": (300, 15000),

        "Bills": (300, 10000),

        "Entertainment": (200, 3000),

        "Salary": (30000, 150000)
    }

    low, high = ranges[category]

    return random.randint(
        low,
        high
    )


def generate_data(
    output_file,
    records_per_category=500
):

    rows = []

    start_date = date(
        2025,
        1,
        1
    )

    for category, examples in CATEGORY_DATA.items():

        for _ in range(records_per_category):

            description, merchant = random.choice(
                examples
            )

            amount = random_amount(
                category
            )

            random_days = random.randint(
                0,
                600
            )

            transaction_date = (
                start_date
                + timedelta(
                    days=random_days
                )
            )

            rows.append([
                transaction_date.isoformat(),
                description,
                amount,
                "income"
                if category == "Salary"
                else "expense",
                merchant,
                category
            ])

    random.shuffle(rows)

    with open(
        output_file,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow([
            "date",
            "description",
            "amount",
            "type",
            "merchant",
            "category"
        ])

        writer.writerows(rows)

    print(
        f"Generated {len(rows)} transactions."
    )


if __name__ == "__main__":

    generate_data(
        "data/ml/large_training_data.csv"
    )