from src.services.category_service import CategoryService


def add_categories(df):

    category_service = CategoryService()

    df = df.copy()

    df["category"] = df.apply(
        lambda row: category_service.categorize(
            row["description"],
            row["merchant"]
        ),
        axis=1
    )

    return df