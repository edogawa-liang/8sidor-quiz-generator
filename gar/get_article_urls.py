import requests
from lxml import html
from urllib.parse import urljoin, urlparse, urldefrag
import re
import time


BASE_URL = "https://8sidor.se"


def get_page_url(category, page):
    """
    Generate the URL for a specific category page.

    Args:
        category (str): News category name.
        page (int): Page number.

    Returns:
        str: Category page URL.
    """

    if page == 1:
        return f"{BASE_URL}/kategori/{category}/"

    return f"{BASE_URL}/kategori/{category}/page/{page}/"


def get_article_urls(page_url, category):
    """
    Extract unique article URLs from a category page.

    Args:
        page_url (str): Category page URL.
        category (str): News category name.

    Returns:
        list[str]: Unique article URLs without fragments.
    """

    response = requests.get(
        page_url,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    response.raise_for_status()

    tree = html.fromstring(response.content)

    # Extract links from article elements
    links = tree.xpath('//article//a[@href]/@href')

    article_urls = []

    pattern = (
        rf"/{re.escape(category)}/"
        rf"\d{{4}}/\d{{2}}/[^/]+/?"
    )

    for link in links:

        # Convert relative URLs to absolute URLs
        full_url = urljoin(page_url, link)

        # Remove URL fragments such as #comments
        full_url, _ = urldefrag(full_url)

        # Extract URL path
        parsed_url = urlparse(full_url)
        path = parsed_url.path

        # Keep only valid article URLs
        if (
            parsed_url.netloc == "8sidor.se"
            and re.fullmatch(pattern, path)
        ):
            article_urls.append(full_url)

    # Remove duplicate URLs while preserving order
    return list(dict.fromkeys(article_urls))


def scrape_article_urls(category="varlden", max_pages=10):
    """
    Collect article URLs from multiple category pages.

    Args:
        category (str): News category name.
        max_pages (int): Maximum number of pages to scrape.

    Returns:
        list[str]: Unique article URLs.
    """

    all_urls = []
    seen = set()

    for page in range(1, max_pages + 1):

        # Generate the current page URL
        page_url = get_page_url(category, page)

        print(f"Scraping page {page}: {page_url}")

        try:

            # Extract article URLs from the current page
            urls = get_article_urls(page_url, category)

            if not urls:
                print("No articles found. Stopping.")
                break

            new_count = 0

            for url in urls:

                if url not in seen:

                    seen.add(url)
                    all_urls.append(url)

                    new_count += 1

            print(f"Found {new_count} new article URLs")

            if new_count == 0:
                print("No new URLs found. Stopping.")
                break

            # Add a delay between requests
            time.sleep(2)

        except requests.RequestException as e:

            print(f"Request failed: {e}")
            break

    print(f"\nTotal article URLs collected: {len(all_urls)}")

    return all_urls