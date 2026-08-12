class CategoryService:

    CATEGORY_RULES = {

        "Food": [
            "swiggy",
            "zomato",
            "restaurant",
            "food",
            "cafe"
        ],

        "Transport": [
            "uber",
            "ola",
            "fuel",
            "petrol",
            "diesel",
            "bus",
            "train"
        ],

        "Shopping": [
            "amazon",
            "flipkart",
            "shopping",
            "dmart"
        ],

        "Bills": [
            "electricity",
            "water",
            "internet",
            "mobile",
            "bill"
        ],

        "Entertainment": [
            "netflix",
            "spotify",
            "movie"
        ],

        "Salary": [
            "salary"
        ]
    }


    def categorize(self, description, merchant=""):

        text = (
            f"{description} {merchant}"
            .lower()
        )

        for category, keywords in self.CATEGORY_RULES.items():

            for keyword in keywords:

                if keyword in text:

                    return category

        return "Other"