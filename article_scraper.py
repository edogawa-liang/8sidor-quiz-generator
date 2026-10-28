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
        start_page=1,
        max_pages=3,
        max_articles=10,
        delay=2
    ):
        """
        Initialize the article scraper.

        Args:
            category (str): News category.
            start_page (int): First category page to scrape.
            max_pages (int): Maximum number of pages to scrape.
            max_articles (int): Maximum number of articles.
            delay (float): Delay between HTTP requests.
        """

        if start_page < 1:
            raise ValueError("start_page must be at least 1.")

        if max_pages < 1 or max_articles < 1:
            raise ValueError(
                "max_pages and max_articles must be positive."
            )

        self.category = category.strip("/")
        self.start_page = start_page
        self.max_pages = max_pages
        self.max_articles = max_articles
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
        """Read article metadata from the category listing (no article requests)."""
        response = self.session.get(page_url, timeout=20)
        response.raise_for_status()
        tree = html.fromstring(response.content)
        pattern = rf"/{re.escape(self.category)}/\d{{4}}/\d{{2}}/[^/]+/?"
        results = []
        seen = set()

        # The listing card contains an excerpt and a sibling .bottom-links date.
        # Search the nearest card ancestor for each excerpt, rather than
        # accidentally assigning another card's date.
        for excerpt in tree.xpath('//div[contains(concat(" ", normalize-space(@class), " "), " excerpt ")][@data-url]'):
            url = urljoin(page_url, excerpt.get('data-url'))
            url, _ = urldefrag(url)
            parsed = urlparse(url)
            if parsed.netloc not in ('8sidor.se', 'www.8sidor.se') or not re.fullmatch(pattern, parsed.path):
                continue
            if url in seen:
                continue

            date = None
            title = None
            # Climb from the excerpt until we find the corresponding date.
            card = excerpt
            for _ in range(5):
                parent = card.getparent()
                if parent is None or parent.tag == 'body':
                    break
                card = parent
                dates = card.xpath('.//p[contains(concat(" ", normalize-space(@class), " "), " bottom-links ")]//span[contains(concat(" ", normalize-space(@class), " "), " date ")]')
                if dates:
                    date = self.parse_swedish_date(dates[0].text_content().strip())
                    headings = card.xpath('.//h2 | .//h3 | .//h4')
                    if headings:
                        title = headings[0].text_content().strip()
                    break

            seen.add(url)
            results.append({'url': url, 'title': title, 'date': date})

        return results

    def scrape_article_urls(self):
        """Collect at most max_articles entries, up to max_pages pages."""
        articles = []
        seen = set()
        end_page = self.start_page + self.max_pages

        for page in range(self.start_page, end_page):
            page_url = self.get_page_url(page)
            print(
                f"\nScraping listing page {page}: {page_url}"
            )
            try:
                items = self.get_article_urls(page_url)
            except requests.RequestException as e:
                print(f"Request failed: {e}")
                break
            if not items:
                print('No articles found. Stopping.')
                break
            new_count = 0
            for item in items:
                if item['url'] in seen:
                    continue
                seen.add(item['url'])
                articles.append(item)
                new_count += 1
                if len(articles) >= self.max_articles:
                    break
            print(f"Collected {len(articles)}/{self.max_articles} articles")
            if len(articles) >= self.max_articles or new_count == 0:
                break
            if page < end_page - 1:
                time.sleep(self.delay)
        return articles

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

    def get_article_text(self, url, listing_date=None, listing_title=None):
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

        title = listing_title or (
            title_elements[0].text_content().strip()
            if title_elements
            else None
        )

        # Date already extracted from listing page; no need to look it up here.
        date = listing_date

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

    def scrape_articles(self, entries):
        """
        Extract article information from multiple URLs.

        Args:
            urls (list[str]): Article URLs.

        Returns:
            list[dict]: Extracted article data.
        """

        articles = []

        total = len(entries)

        for index, entry in enumerate(
            entries,
            start=1
        ):

            print(
                f"\nScraping article {index}/{total}"
            )

            try:

                article = self.get_article_text(
                    entry["url"], entry["date"], entry["title"]
                )

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
                        f"Article text not found: {entry['url']}"
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
        print(f"Start page: {self.start_page}")
        print(f"Category: {self.category}")
        print(f"Max pages: {self.max_pages}")
        print(f"Max articles: {self.max_articles}")
        print(f"Request delay: {self.delay} seconds")
        print("=" * 50)

        # Step 1: Collect article URLs
        print("\n[Step 1] Collecting article URLs...")

        entries = self.scrape_article_urls()

        if not entries:
            print("No article URLs found.")
            return []

        # Step 2: Extract article data
        print("\n[Step 2] Extracting article data...")

        articles = self.scrape_articles(entries)

        print("\n" + "=" * 50)
        print("Scraping completed!")
        print(f"Total listing entries: {len(entries)}")
        print(f"Total articles: {len(articles)}")
        print("=" * 50)

        return articles

    def close(self):
        """
        Close the HTTP session.
        """

        self.session.close()

if __name__ == "__main__":
    scraper = ArticleScraper(category="varlden", start_page=3, max_pages=3, max_articles=10, delay=2)
    try:
        articles = scraper.run()
        import json
        with open("articles.json", "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        print(f"Saved {len(articles)} articles to articles.json")
    finally:
        scraper.close()
