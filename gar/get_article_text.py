import requests
from lxml import html
import time
import json
from datetime import datetime


def get_article_text(url):
    """
    Extract the publication date, title, and text
    from a single article.

    Args:
        url (str): Article URL.

    Returns:
        dict: Article information containing:
            - url
            - date
            - title
            - text
    """

    response = requests.get(
        url,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    response.raise_for_status()

    # Parse the HTML content
    tree = html.fromstring(response.content)

    # ==========================
    # 1. Extract article title
    # ==========================

    title_elements = tree.xpath(
        "//h1"
    )

    title = (
        title_elements[0].text_content().strip()
        if title_elements
        else None
    )

    # ==========================
    # 2. Extract publication date
    # ==========================

    date_elements = tree.xpath(
        '//p[contains(concat(" ", normalize-space(@class), " "), " date ")]/text()'
    )

    date = date_elements[0].strip() if date_elements else None

    # ==========================
    # 3. Extract article text
    # ==========================

    # Find paragraphs inside the article content container
    paragraphs = tree.xpath(
        '//div[starts-with(@id, "rspeak_read_")]//p'
    )

    text_list = []

    for p in paragraphs:

        # Extract text including nested HTML elements
        text = " ".join(p.itertext()).strip()

        # Normalize whitespace
        text = " ".join(text.split())

        if text:
            text_list.append(text)

    # Combine paragraphs into a single text string
    article_text = "\n\n".join(text_list)

    # ==========================
    # 4. Return article data
    # ==========================

    return {
        "url": url,
        "date": date,
        "title": title,
        "text": article_text
    }


def scrape_articles(urls, delay=2):
    """
    Extract article information from multiple URLs.

    Args:
        urls (list[str]): List of article URLs.
        delay (int): Delay between requests in seconds.

    Returns:
        list[dict]: List of extracted article data.
    """

    articles = []

    total = len(urls)

    for index, url in enumerate(urls, start=1):

        print(f"\nScraping article {index}/{total}")

        try:

            # Extract information from the current article
            article = get_article_text(url)

            if article["text"]:

                articles.append(article)

                print("Date:", article["date"])
                print("Title:", article["title"])
                print("Text length:", len(article["text"]))

            else:
                print("Article text not found:", url)

        except requests.RequestException as e:

            print("Request failed:", e)

        # Add a delay before the next request
        if index < total:
            time.sleep(delay)

    print(f"\nSuccessfully scraped {len(articles)} articles")

    return articles