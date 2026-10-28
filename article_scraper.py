import re
import time
import requests

from datetime import datetime
from lxml import html
from urllib.parse import urljoin, urlparse, urldefrag


class ArticleScraper:
    """
    Scrape article URLs and article content from 8 Sidor.
    """

    BASE_URL = "https://8sidor.se"

    SWEDISH_MONTHS = {
        "januari": 1,
        "februari": 2,
        "mars": 3,
        "april": 4,
        "maj": 5,
        "juni": 6,
        "juli": 7,
        "augusti": 8,
        "september": 9,
        "oktober": 10,
        "november": 11,
        "december": 12
    }

    def __init__(
        self,
        category="varlden",
        max_pages=3,
        delay=2
    ):
        """
        Initialize the article scraper.

        Args:
            category (str): News category.
            max_pages (int): Maximum number of category pages.
            delay (float): Delay between HTTP requests.
        """

        self.category = category.strip("/")
        self.max_pages = max_pages
        self.delay = delay

        # Create a reusable HTTP session
        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": "Mozilla/5.0"
        })

    def get_page_url(self, page):
        """
        Generate a category page URL.

        Args:
            page (int): Page number.

        Returns:
            str: Category page URL.
        """

        if page == 1:
            return (
                f"{self.BASE_URL}/kategori/"
                f"{self.category}/"
            )

        return (
            f"{self.BASE_URL}/kategori/"
            f"{self.category}/page/{page}/"
        )

    def get_article_urls(self, page_url):
        """
        Extract unique article URLs from a category page.

        Args:
            page_url (str): Category page URL.

        Returns:
            list[str]: Unique article URLs.
        """

        response = self.session.get(
            page_url,
            timeout=20
        )

        response.raise_for_status()

        # Parse HTML
        tree = html.fromstring(response.content)

        # Extract links from article elements
        links = tree.xpath(
            '//article//a[@href]/@href'
        )

        article_urls = []

        # Match article URL paths
        pattern = (
            rf"/{re.escape(self.category)}/"
            rf"\d{{4}}/\d{{2}}/[^/]+/?"
        )

        for link in links:

            # Convert relative URLs to absolute URLs
            full_url = urljoin(page_url, link)

            # Remove fragments such as #comments
            full_url, _ = urldefrag(full_url)

            # Parse the URL
            parsed_url = urlparse(full_url)

            path = parsed_url.path

            # Keep only valid article URLs
            if (
                parsed_url.netloc == "8sidor.se"
                and re.fullmatch(pattern, path)
            ):
                article_urls.append(full_url)

        # Remove duplicates while preserving order
        return list(dict.fromkeys(article_urls))

    def scrape_article_urls(self):
        """
        Collect article URLs from multiple category pages.

        Returns:
            list[str]: Unique article URLs.
        """

        all_urls = []
        seen = set()

        for page in range(1, self.max_pages + 1):

            page_url = self.get_page_url(page)

            print(
                f"\nScraping page {page}/{self.max_pages}"
            )

            print(f"URL: {page_url}")

            try:

                urls = self.get_article_urls(page_url)

                if not urls:
                    print("No articles found. Stopping.")
                    break

                new_count = 0

                for url in urls:

                    if url not in seen:

                        seen.add(url)
                        all_urls.append(url)

                        new_count += 1

                print(
                    f"Found {new_count} new article URLs"
                )

                if new_count == 0:
                    print("No new URLs found. Stopping.")
                    break

            except requests.RequestException as e:

                print(f"Request failed: {e}")
                break

            # Add a delay between category page requests
            if page < self.max_pages:
                time.sleep(self.delay)

        print(
            f"\nTotal article URLs collected: "
            f"{len(all_urls)}"
        )

        return all_urls

    def parse_swedish_date(self, date_string):
        """
        Convert a Swedish date string to ISO format.

        Example:
            "19 oktober 2026" -> "2026-10-19"

        Args:
            date_string (str): Swedish date string.

        Returns:
            str | None: Date in YYYY-MM-DD format.
        """

        if not date_string:
            return None

        parts = date_string.lower().strip().split()

        if len(parts) != 3:
            return None

        day, month_name, year = parts

        month = self.SWEDISH_MONTHS.get(month_name)

        if month is None:
            return None

        try:

            parsed_date = datetime(
                int(year),
                month,
                int(day)
            )

            return parsed_date.strftime("%Y-%m-%d")

        except ValueError:
            return None

    def get_article_text(self, url):
        """
        Extract article title, date, and text.

        Args:
            url (str): Article URL.

        Returns:
            dict: Article information containing:
                - url
                - date
                - title
                - text
        """

        response = self.session.get(
            url,
            timeout=20
        )

        response.raise_for_status()

        # Parse HTML
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
            '//p[contains(concat(" ", '
            'normalize-space(@class), " "), '
            '" date ")]'
        )

        if date_elements:

            # Extract the Swedish date
            raw_date = (
                date_elements[0]
                .text_content()
                .strip()
            )

            # Convert to ISO format
            date = self.parse_swedish_date(
                raw_date
            )

        else:
            date = None

        # ==========================
        # 3. Extract article text
        # ==========================

        paragraphs = tree.xpath(
            '//div[starts-with(@id, "rspeak_read_")]//p'
        )

        text_list = []

        for p in paragraphs:

            # Extract text including nested elements
            text = " ".join(p.itertext()).strip()

            # Normalize whitespace
            text = " ".join(text.split())

            if text:
                text_list.append(text)

        # Combine paragraphs
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

    def scrape_articles(self, urls):
        """
        Extract article information from multiple URLs.

        Args:
            urls (list[str]): Article URLs.

        Returns:
            list[dict]: Extracted article data.
        """

        articles = []

        total = len(urls)

        for index, url in enumerate(
            urls,
            start=1
        ):

            print(
                f"\nScraping article {index}/{total}"
            )

            try:

                article = self.get_article_text(url)

                if article["text"]:

                    articles.append(article)

                    print(
                        f"Date: {article['date']}"
                    )

                    print(
                        f"Title: {article['title']}"
                    )

                    print(
                        f"Text length: "
                        f"{len(article['text'])}"
                    )

                else:

                    print(
                        f"Article text not found: {url}"
                    )

            except requests.RequestException as e:

                print(f"Request failed: {e}")

            # Add a delay between article requests
            if index < total:
                time.sleep(self.delay)

        print(
            f"\nSuccessfully scraped "
            f"{len(articles)} articles"
        )

        return articles

    def run(self):
        """
        Run the complete article scraping pipeline.

        Returns:
            list[dict]: Extracted article data.
        """

        print("=" * 50)
        print("8 Sidor Article Scraper")
        print(f"Category: {self.category}")
        print(f"Max pages: {self.max_pages}")
        print(f"Request delay: {self.delay} seconds")
        print("=" * 50)

        # Step 1: Collect article URLs
        print("\n[Step 1] Collecting article URLs...")

        urls = self.scrape_article_urls()

        if not urls:
            print("No article URLs found.")
            return []

        # Step 2: Extract article data
        print("\n[Step 2] Extracting article data...")

        articles = self.scrape_articles(urls)

        print("\n" + "=" * 50)
        print("Scraping completed!")
        print(f"Total URLs: {len(urls)}")
        print(f"Total articles: {len(articles)}")
        print("=" * 50)

        return articles

    def close(self):
        """
        Close the HTTP session.
        """

        self.session.close()