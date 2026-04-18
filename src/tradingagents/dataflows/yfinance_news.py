"""yfinance-based news data fetching functions."""

import contextlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import yfinance as yf
from dateutil.relativedelta import relativedelta

from .constants import (
    NEWS_DEFAULT_LIMIT_YFINANCE,
    NEWS_DEFAULT_LOOKBACK_DAYS,
    NEWS_FETCH_COUNT_YFINANCE,
)
from .exceptions import VendorError
from .logging_config import y_finance_logger


def _fetch_search_parallel(queries: list[str], news_count: int = 10) -> list:
    """Fetch multiple search queries in parallel and return combined news results."""
    with ThreadPoolExecutor(max_workers=4) as executor:
        return list(
            executor.map(
                lambda q: (
                    yf.Search(q, news_count=news_count, enable_fuzzy_query=True).news
                ),
                queries,
            )
        )


def _extract_article_data(article: dict) -> dict[str, str | datetime | None]:
    """Extract article data from yfinance news format (handles nested 'content' structure)."""
    # Handle nested content structure
    if "content" in article:
        content = article["content"]
        title = content.get("title", "No title")
        summary = content.get("summary", "")
        provider = content.get("provider", {})
        publisher = provider.get("displayName", "Unknown")

        # Get URL from canonicalUrl or clickThroughUrl
        url_obj = content.get("canonicalUrl") or content.get("clickThroughUrl") or {}
        link = url_obj.get("url", "")

        # Get publish date
        pub_date_str = content.get("pubDate", "")
        pub_date = None
        if pub_date_str:
            with contextlib.suppress(ValueError, AttributeError):
                pub_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))

        return {
            "title": title,
            "summary": summary,
            "publisher": publisher,
            "link": link,
            "pub_date": pub_date,
        }
    # Fallback for flat structure
    return {
        "title": article.get("title", "No title"),
        "summary": article.get("summary", ""),
        "publisher": article.get("publisher", "Unknown"),
        "link": article.get("link", ""),
        "pub_date": None,
    }


def get_news_yfinance(
    ticker: str,
    start_date: str,
    end_date: str,
) -> str:
    """
    Retrieve news for a specific stock ticker using yfinance.

    Args:
        ticker: Stock ticker symbol (e.g., "AAPL")
        start_date: Start date in yyyy-mm-dd format
        end_date: End date in yyyy-mm-dd format

    Returns:
        Formatted string containing news articles
    """
    try:
        stock = yf.Ticker(ticker)
        news = stock.get_news(count=NEWS_FETCH_COUNT_YFINANCE)

        if not news:
            return f"No news found for {ticker}"

        # Parse date range for filtering
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        news_str = ""
        filtered_count = 0

        for article in news:
            data = _extract_article_data(article)

            # Filter by date if publish time is available
            pub_date = data["pub_date"]
            if isinstance(pub_date, datetime):
                pub_date_naive = pub_date.replace(tzinfo=None)
                if not (start_dt <= pub_date_naive <= end_dt + relativedelta(days=1)):
                    continue

            news_str += f"### {data['title']} (source: {data['publisher']})\n"
            if data["summary"]:
                news_str += f"{data['summary']}\n"
            if data["link"]:
                news_str += f"Link: {data['link']}\n"
            news_str += "\n"
            filtered_count += 1

        if filtered_count == 0:
            return f"No news found for {ticker} between {start_date} and {end_date}"

        return f"## {ticker} News, from {start_date} to {end_date}:\n\n{news_str}"

    except Exception as e:
        error_msg = f"Error fetching news for {ticker}"
        y_finance_logger.error(f"{error_msg}: {e}")
        raise VendorError(
            error_msg,
            function="get_news_yfinance",
            vendor="yfinance",
            params={"ticker": ticker, "start_date": start_date, "end_date": end_date},
            original_error=e,
        )


def get_global_news_yfinance(
    curr_date: str,
    look_back_days: int = NEWS_DEFAULT_LOOKBACK_DAYS,
    limit: int = NEWS_DEFAULT_LIMIT_YFINANCE,
) -> str:
    """
    Retrieve global/macro economic news using yfinance Search.

    Args:
        curr_date: Current date in yyyy-mm-dd format
        look_back_days: Number of days to look back
        limit: Maximum number of articles to return

    Returns:
        Formatted string containing global news articles
    """
    search_queries = [
        "stock market economy",
        "Federal Reserve interest rates",
        "inflation economic outlook",
        "global markets trading",
    ]

    all_news = []
    seen_titles = set()

    try:
        search_results = _fetch_search_parallel(search_queries, limit)

        for news_list in search_results:
            if not news_list:
                continue

            for article in news_list:
                if "content" in article:
                    data = _extract_article_data(article)
                    title = data["title"]
                else:
                    title = article.get("title", "")

                if title and title not in seen_titles:
                    seen_titles.add(title)
                    all_news.append(article)

                if len(all_news) >= limit:
                    break

            if len(all_news) >= limit:
                break

        if not all_news:
            return f"No global news found for {curr_date}"

        # Calculate date range
        curr_dt = datetime.strptime(curr_date, "%Y-%m-%d")
        start_dt = curr_dt - relativedelta(days=look_back_days)
        start_date = start_dt.strftime("%Y-%m-%d")

        news_str = ""
        for article in all_news[:limit]:
            # Handle both flat and nested structures
            if "content" in article:
                data = _extract_article_data(article)
                title = data["title"]
                publisher = data["publisher"]
                link = data["link"]
                summary = data["summary"]
            else:
                title = article.get("title", "No title")
                publisher = article.get("publisher", "Unknown")
                link = article.get("link", "")
                summary = ""

            news_str += f"### {title} (source: {publisher})\n"
            if summary:
                news_str += f"{summary}\n"
            if link:
                news_str += f"Link: {link}\n"
            news_str += "\n"

        return f"## Global Market News, from {start_date} to {curr_date}:\n\n{news_str}"

    except Exception as e:
        error_msg = "Error fetching global news"
        y_finance_logger.error(f"{error_msg}: {e}")
        raise VendorError(
            error_msg,
            function="get_global_news_yfinance",
            vendor="yfinance",
            params={
                "curr_date": curr_date,
                "look_back_days": look_back_days,
                "limit": limit,
            },
            original_error=e,
        )
