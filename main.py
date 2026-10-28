import pandas as pd

from pathlib import Path
from datetime import datetime

from article_scraper import ArticleScraper
from generate_quiz import generate_all_quizzes
from create_pdf import create_quiz_pdf


BASE_DIR = Path(__file__).resolve().parent


def save_articles_to_csv(articles, category):
    """
    Save scraped articles to a CSV file.

    Args:
        articles (list[dict]): Scraped article data.
        category (str): News category.

    Returns:
        pd.DataFrame: Article DataFrame.
    """

    df = pd.DataFrame(
        articles,
        columns=["url", "date", "title", "text"]
    )

    output_dir = BASE_DIR / "list"
    output_dir.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")

    filename = f"{category}_{today}.csv"
    output_path = output_dir / filename

    df.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig"
    )

    print(f"CSV saved to: {output_path}")

    return df


def load_articles_from_csv(csv_path):
    """
    Load previously scraped articles from a CSV file.

    Args:
        csv_path (str | Path): Path to the CSV file.

    Returns:
        pd.DataFrame: Article DataFrame.
    """

    df = pd.read_csv(
        csv_path,
        encoding="utf-8-sig"
    )

    print(f"Loaded {len(df)} articles from CSV")

    return df


def main(
    category="varlden",
    start_page=1,
    max_pages=1,
    max_articles=10,
    delay=2,
    model="gpt-4.1-mini",
    use_existing_csv=False,
    csv_path=None
):
    """
    Run the complete article-to-quiz PDF pipeline.

    Args:
        category (str): News category.
        max_pages (int): Maximum number of category pages.
        delay (float): Delay between scraping requests.
        model (str): OpenAI model name.
        use_existing_csv (bool): Load an existing CSV instead of scraping.
        csv_path (str | None): Existing CSV path.

    Returns:
        Path: Generated PDF path.
    """

    print("=" * 50)
    print("8 Sidor - Quiz Generator")
    print(f"Category: {category}")
    print(f"Start page: {start_page}")
    print(f"Max pages: {max_pages}")
    print(f"Max articles: {max_articles}")
    print(f"Request delay: {delay} seconds")
    print(f"Model: {model}")
    print("=" * 50)

    # =====================================
    # Step 1: Load or scrape article data
    # =====================================

    if use_existing_csv:

        print("\n[Step 1] Loading existing CSV...")

        if csv_path is None:
            raise ValueError(
                "csv_path is required when "
                "use_existing_csv=True."
            )

        csv_file = Path(csv_path)

        if not csv_file.is_absolute():
            csv_file = BASE_DIR / csv_file

        df = load_articles_from_csv(csv_file)

    else:

        print("\n[Step 1] Scraping articles...")

        scraper = ArticleScraper(
            category=category,
            start_page=start_page,
            max_pages=max_pages,
            max_articles=max_articles,
            delay=delay
        )

        try:
            articles = scraper.run()

        finally:
            scraper.close()

        if not articles:
            raise ValueError(
                "No articles were scraped."
            )

        # Save a CSV backup
        print("\n[Step 2] Saving CSV backup...")

        df = save_articles_to_csv(
            articles,
            category
        )

    if df.empty:
        raise ValueError("No articles available.")

    # =====================================
    # Step 2: Generate SFI C quizzes
    # =====================================

    print("\n[Step 3] Generating SFI C quizzes...")

    quizzes = generate_all_quizzes(
        df,
        model=model
    )

    # Validate that all articles were processed
    valid_articles = df.dropna(subset=["text"])
    valid_articles = valid_articles[
        valid_articles["text"].astype(str).str.strip() != ""
    ]

    if len(quizzes) != len(valid_articles):
        raise RuntimeError(
            "Some articles failed during quiz generation. "
            "PDF creation stopped to avoid missing articles."
        )

    if not quizzes:
        raise ValueError(
            "No quizzes were generated."
        )

    # =====================================
    # Step 3: Generate PDF
    # =====================================

    print("\n[Step 4] Creating quiz PDF...")

    pdf_path = create_quiz_pdf(
        quizzes,
        output_dir=BASE_DIR / "Quiz",
        category=category
    )

    # =====================================
    # Step 4: Print summary
    # =====================================

    print("\n" + "=" * 50)
    print("Quiz generation completed!")
    print(f"Total articles: {len(quizzes)}")
    print(f"Total questions: {len(quizzes) * 3}")
    print(f"PDF saved to: {pdf_path}")
    print("=" * 50)

    return pdf_path


if __name__ == "__main__":

    pdf_path = main(
        category="varlden",
        start_page=1,
        max_pages=1,
        max_articles=3,
        delay=1,
        model="gpt-4.1-mini",
        use_existing_csv=False
    )