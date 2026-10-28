import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI



# Load environment variables from the project directory
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Read the OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError(
        "OPENAI_API_KEY was not found. "
        "Please check your .env file."
    )

# Initialize the OpenAI client
client = OpenAI(api_key=api_key)


def build_prompt(article):
    """
    Build an SFI C reading exercise prompt.

    Args:
        article (dict): Article information.

    Returns:
        str: Prompt for GPT.
    """

    return f"""
You are an experienced Swedish language teacher
specializing in SFI Kurs C.

Create reading comprehension exercises based ONLY
on the provided Swedish news article.

Requirements:

1. Generate exactly 3 reading comprehension questions.
2. Questions must be written in Swedish.
3. The difficulty should match SFI Kurs C.
4. Questions should test:
   - Main idea
   - Important details
   - Simple reasoning or understanding
5. Provide a short Swedish answer for each question.
6. Extract 5 to 8 important or difficult vocabulary items.
7. Explain vocabulary in Traditional Chinese.
8. Identify 2 to 3 useful Swedish grammar patterns.
9. Explain grammar in Traditional Chinese.
10. Use examples from the article whenever possible.
11. Do not invent information not supported by the article.

Return ONLY a valid JSON object with this structure:

{{
    "questions": [
        {{
            "question": "Swedish question",
            "answer": "Swedish answer"
        }}
    ],
    "vocabulary": [
        {{
            "word": "Swedish word",
            "meaning": "Traditional Chinese meaning",
            "example": "Swedish example sentence"
        }}
    ],
    "grammar": [
        {{
            "pattern": "Swedish grammar pattern",
            "explanation": "Traditional Chinese explanation",
            "example": "Swedish example sentence"
        }}
    ]
}}

Article title:
{article["title"]}

Publication date:
{article["date"]}

Article text:
{article["text"]}
"""


def generate_article_quiz(article, model="gpt-4.1-mini"):
    """
    Generate SFI C exercises for one article.

    Args:
        article (dict): Article information.
        model (str): OpenAI model name.

    Returns:
        dict: Article information and generated exercises.
    """

    prompt = build_prompt(article)

    response = client.responses.create(
        model=model,
        instructions=(
            "You are a Swedish SFI Kurs C teacher. "
            "Return valid JSON only."
        ),
        input=prompt,
        text={
            "format": {
                "type": "json_object"
            }
        }
    )

    quiz = json.loads(response.output_text)

    # Validate the number of questions
    questions = quiz.get("questions", [])

    if len(questions) != 3:
        raise ValueError(
            "GPT did not generate exactly 3 questions."
        )

    return {
        "url": article["url"],
        "date": article["date"],
        "title": article["title"],
        "text": article["text"],
        "questions": questions,
        "vocabulary": quiz.get("vocabulary", []),
        "grammar": quiz.get("grammar", [])
    }


def generate_all_quizzes(
    df,
    model="gpt-4.1-mini",
    delay=1
):
    """
    Generate quizzes for all articles in a DataFrame.

    Args:
        df (pd.DataFrame): Article DataFrame.
        model (str): OpenAI model name.
        delay (float): Delay between API requests.

    Returns:
        list[dict]: Generated exercises for all articles.
    """

    required_columns = {
        "url", "date", "title", "text"
    }

    if not required_columns.issubset(df.columns):
        raise ValueError(
            f"CSV must contain: {required_columns}"
        )

    results = []

    # Remove articles without text
    df = df.dropna(subset=["text"])
    df = df[df["text"].astype(str).str.strip() != ""]

    total = len(df)

    for index, (_, row) in enumerate(
        df.iterrows(),
        start=1
    ):

        article = row.to_dict()

        print(f"\nGenerating quiz {index}/{total}")
        print(f"Title: {article['title']}")

        # Retry temporary failures
        for attempt in range(3):

            try:
                result = generate_article_quiz(
                    article,
                    model=model
                )

                results.append(result)

                print("Quiz generated successfully.")
                break

            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")

                if attempt == 2:
                    print("Skipping this article.")
                else:
                    time.sleep(3 * (attempt + 1))

        if index < total:
            time.sleep(delay)

    print(f"\nGenerated {len(results)}/{total} quizzes")

    return results


def load_articles(csv_path):
    """
    Load article data from a CSV file.

    Args:
        csv_path (str): Path to the CSV file.

    Returns:
        pd.DataFrame: Article DataFrame.
    """

    df = pd.read_csv(
        csv_path,
        encoding="utf-8-sig"
    )

    print(f"Loaded {len(df)} articles")

    return df