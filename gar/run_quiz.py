from pathlib import Path
from datetime import datetime

from generate_quiz import (
    load_articles,
    generate_all_quizzes
)

from create_pdf import create_quiz_pdf


def main(
    csv_path=None,
    model="gpt-4.1-mini"
):
    """
    Generate an SFI C quiz PDF from an article CSV.

    Args:
        csv_path (str | None): Input CSV path.
        model (str): OpenAI model name.

    Returns:
        Path: Generated PDF path.
    """

    print("=" * 50)
    print("8 Sidor - SFI C Quiz Generator")
    print("=" * 50)

    # Step 1: Locate the CSV file
    if csv_path is None:

        csv_files = list(
            Path("list").glob("8sidor_upadate_*.csv")
        )

        if not csv_files:
            raise FileNotFoundError(
                "No article CSV files found."
            )

        # Select the most recently modified CSV
        csv_path = max(
            csv_files,
            key=lambda p: p.stat().st_mtime
        )

    print(f"\nInput CSV: {csv_path}")

    # Step 2: Load articles
    print("\n[Step 1] Loading articles...")

    df = load_articles(csv_path)

    # Step 3: Generate exercises using GPT
    print("\n[Step 2] Generating SFI C exercises...")

    quizzes = generate_all_quizzes(
        df,
        model=model
    )

    # Stop if any article was not processed
    valid_articles = df.dropna(subset=["text"])
    valid_articles = valid_articles[
        valid_articles["text"].astype(str).str.strip() != ""
    ]

    if len(quizzes) != len(valid_articles):
        raise RuntimeError(
            "Some articles failed during quiz generation. "
            "PDF creation stopped to avoid an incomplete result."
        )

    # Step 4: Generate PDF
    print("\n[Step 3] Creating PDF...")

    pdf_path = create_quiz_pdf(
        quizzes,
        output_dir="quiz"
    )

    print("\n" + "=" * 50)
    print("Quiz generation completed!")
    print(f"Total articles: {len(quizzes)}")
    print(f"Output: {pdf_path}")
    print("=" * 50)

    return pdf_path


if __name__ == "__main__":

    pdf_path = main(
        csv_path=None,
        model="gpt-4.1-mini"
    )