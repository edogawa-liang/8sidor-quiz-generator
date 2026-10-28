import json
import os
import time
from pathlib import Path
import random

import pandas as pd
from dotenv import load_dotenv
from openai import (
    OpenAI,
    BadRequestError,
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
)

BASE_DIR = Path(__file__).resolve().parent
PROMPT_PATH = BASE_DIR / "prompts" / "quiz.txt"

load_dotenv(BASE_DIR / ".env")

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError(
        "OPENAI_API_KEY was not found. Please check your .env file."
    )

client = OpenAI(api_key=api_key)

def shuffle_correct_answers(questions):
    """Randomize answer positions independently for each question."""

    for question in questions:
        old_options = question["options"]
        correct_answer = question["correct_answer"]

        # Store the correct answer text before shuffling
        correct_text = old_options[correct_answer]

        # Shuffle all option texts
        option_texts = [
            old_options[letter]
            for letter in ("A", "B", "C")
        ]

        random.shuffle(option_texts)

        # Assign shuffled texts to A, B, and C
        question["options"] = dict(
            zip(("A", "B", "C"), option_texts)
        )

        # Update the correct answer position
        question["correct_answer"] = next(
            letter
            for letter, text in question["options"].items()
            if text == correct_text
        )

    return questions

def load_prompt():
    """Load reusable instructions from a UTF-8 text file."""

    if not PROMPT_PATH.is_file():
        raise FileNotFoundError(
            f"Prompt file not found: {PROMPT_PATH}"
        )

    prompt = PROMPT_PATH.read_text(
        encoding="utf-8"
    ).strip()

    if not prompt:
        raise ValueError("Prompt file is empty.")

    return prompt


def build_prompt(article):
    """Build the article input for the OpenAI API."""

    return (
        "Generate listening comprehension exercises "
        "and return a valid JSON object.\n\n"
        f"Article title:\n{article['title']}\n\n"
        f"Publication date:\n{article['date']}\n\n"
        f"Article text:\n{article['text']}"
    )


def validate_quiz(quiz):
    """Validate the generated quiz structure."""

    if not isinstance(quiz, dict):
        raise ValueError("Quiz response must be a JSON object.")

    # Validate questions
    questions = quiz.get("questions")

    if not isinstance(questions, list) or len(questions) != 3:
        raise ValueError(
            "GPT must generate exactly 3 questions."
        )

    for index, question in enumerate(questions, start=1):

        if not isinstance(question, dict):
            raise ValueError(
                f"Question {index} must be an object."
            )

        if not isinstance(question.get("question"), str) or not question["question"].strip():
            raise ValueError(
                f"Question {index} is missing question text."
            )

        options = question.get("options")

        if not isinstance(options, dict):
            raise ValueError(
                f"Question {index} options must be an object."
            )

        if set(options.keys()) != {"A", "B", "C"}:
            raise ValueError(
                f"Question {index} must contain options A, B, and C."
            )

        for key, value in options.items():

            if not isinstance(value, str) or not value.strip():
                raise ValueError(
                    f"Question {index}, option {key} is invalid."
                )

        if question.get("correct_answer") not in {"A", "B", "C"}:
            raise ValueError(
                f"Question {index} has an invalid correct answer."
            )

    # Validate vocabulary
    vocabulary = quiz.get("vocabulary")

    if not isinstance(vocabulary, list):
        raise ValueError(
            "Vocabulary must be a list."
        )

    for index, item in enumerate(vocabulary, start=1):

        if not isinstance(item, dict):
            raise ValueError(
                f"Vocabulary item {index} must be an object."
            )

        for field in (
            "word_sv",
            "meaning_en",
            "word_forms",
        ):

            if not isinstance(item.get(field), str):
                raise ValueError(
                    f"Vocabulary item {index} is missing {field}."
                )

    # Validate useful expressions
    expressions = quiz.get("expressions")

    if not isinstance(expressions, list):
        raise ValueError(
            "Expressions must be a list."
        )

    for index, item in enumerate(expressions, start=1):

        if not isinstance(item, dict):
            raise ValueError(
                f"Expression item {index} must be an object."
            )

        for field in (
            "expression_sv",
            "meaning_en",
        ):

            if not isinstance(item.get(field), str):
                raise ValueError(
                    f"Expression item {index} is missing {field}."
                )

    return quiz


def generate_article_quiz(
    article,
    instructions,
    model="gpt-4.1-mini",
    max_attempts=3,
):
    """Generate listening comprehension exercises with automatic retries."""

    prompt = build_prompt(article)

    for attempt in range(1, max_attempts + 1):
        try:
            response = client.responses.create(
                model=model,
                instructions=instructions,
                input=prompt,
                text={
                    "format": {
                        "type": "json_object"
                    }
                },
            )

            if not response.output_text:
                raise ValueError("OpenAI returned an empty response.")

            quiz = json.loads(response.output_text)

            # Validate quiz structure
            validate_quiz(quiz)

            # Randomize correct answer positions
            quiz["questions"] = shuffle_correct_answers(
                quiz["questions"]
            )

            return {
                **article,
                "questions": quiz["questions"],
                "vocabulary": quiz["vocabulary"],
                "expressions": quiz["expressions"],
            }

        except (ValueError, json.JSONDecodeError) as e:
            print(
                f"Quiz generation failed "
                f"(attempt {attempt}/{max_attempts}): {e}"
            )

            if attempt == max_attempts:
                raise

            print("Retrying quiz generation...")


def generate_all_quizzes(
    df,
    model="gpt-4.1-mini",
    delay=1,
):
    """Generate quizzes for all nonempty articles."""

    required_columns = {
        "url",
        "date",
        "title",
        "text",
    }

    if not required_columns.issubset(df.columns):
        raise ValueError(
            f"CSV must contain: {required_columns}"
        )

    # Load instructions once
    instructions = load_prompt()

    valid_df = df.dropna(subset=["text"])

    valid_df = valid_df[
        valid_df["text"].astype(str).str.strip() != ""
    ]

    results = []
    total = len(valid_df)

    retryable_errors = (
        RateLimitError,
        APIConnectionError,
        APITimeoutError,
        InternalServerError,
    )

    for index, (_, row) in enumerate(
        valid_df.iterrows(),
        start=1,
    ):

        article = row.to_dict()

        print(f"\nGenerating quiz {index}/{total}")
        print(f"Title: {article['title']}")

        for attempt in range(3):

            try:
                result = generate_article_quiz(
                    article=article,
                    instructions=instructions,
                    model=model,
                )

                results.append(result)

                print("Quiz generated successfully.")

                break

            except BadRequestError as exc:
                print(f"Invalid API request: {exc}")
                raise

            except retryable_errors as exc:
                print(
                    f"Attempt {attempt + 1} failed: {exc}"
                )

                if attempt == 2:
                    print("Skipping this article.")
                else:
                    time.sleep(3 * (attempt + 1))

            except Exception as exc:
                print(f"Quiz generation failed: {exc}")
                raise

        if index < total:
            time.sleep(delay)

    print(
        f"\nGenerated {len(results)}/{total} quizzes"
    )

    return results


def load_articles(csv_path):
    """Load article data from a UTF-8-SIG CSV file."""

    df = pd.read_csv(
        csv_path,
        encoding="utf-8-sig",
    )

    print(f"Loaded {len(df)} articles")

    return df