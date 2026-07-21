import requests
import feedparser
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY")

ENERGY_KEYWORDS = [
    "Strait of Hormuz",
    "Red Sea attack",
    "Iran sanctions",
    "OPEC cut",
    "Houthi tanker",
    "crude oil supply disruption",
    "Persian Gulf naval",
    "Bab el-Mandeb",
]

RSS_FEEDS = [
    "https://www.eia.gov/rss/press_releases.xml",
    "https://rss.app/feeds/oil-energy-news.xml",
    "https://www.rigzone.com/news/rss/rigzone_latest.aspx",
]
def fetch_newsapi():
    print("[NewsAPI] Fetching articles...")
    query = " OR ".join(f'"{kw}"' for kw in ENERGY_KEYWORDS)
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "sortBy": "publishedAt",
        "apiKey": NEWSAPI_KEY,
        "language": "en",
        "pageSize": 20,
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        articles = response.json().get("articles", [])
        results = []
        for a in articles:
            results.append({
                "title":     a.get("title", ""),
                "summary":   a.get("description", ""),
                "source":    a.get("source", {}).get("name", "NewsAPI"),
                "url":       a.get("url", ""),
                "published": a.get("publishedAt", ""),
                "feed":      "newsapi",
            })
        print(f"[NewsAPI] Got {len(results)} articles")
        return results
    except Exception as e:
        print(f"[NewsAPI] Error: {e}")
        return []

def fetch_rss():
    print("[RSS] Fetching feeds...")
    all_articles = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries:
                all_articles.append({
                    "title":     entry.get("title", ""),
                    "summary":   entry.get("summary", ""),
                    "source":    feed.feed.get("title", feed_url),
                    "url":       entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "feed":      "rss",
                })
        except Exception as e:
            print(f"[RSS] Error on {feed_url}: {e}")
    print(f"[RSS] Got {len(all_articles)} articles")
    return all_articles

def fetch_gdelt():
    print("[GDELT] Fetching latest events...")
    try:
        url = "https://api.gdeltproject.org/api/v2/doc/doc"
        params = {
            "query":      "oil supply disruption Hormuz Red Sea sanctions",
            "mode":       "artlist",
            "maxrecords": 20,
            "format":     "json",
        }
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        articles = data.get("articles", [])
        results = []
        for a in articles:
            results.append({
                "title":     a.get("title", ""),
                "summary":   a.get("title", ""),
                "source":    a.get("domain", "GDELT"),
                "url":       a.get("url", ""),
                "published": a.get("seendate", ""),
                "feed":      "gdelt",
            })
        print(f"[GDELT] Got {len(results)} articles")
        return results
    except Exception as e:
        print(f"[GDELT] Error: {e}")
        return []

def deduplicate(articles):
    seen_titles = set()
    unique = []
    for a in articles:
        title_clean = a["title"].lower().strip()
        if title_clean not in seen_titles and title_clean != "":
            seen_titles.add(title_clean)
            unique.append(a)
    return unique

def fetch_all_news():
    print(f"\n{'='*50}")
    print(f"Fetching news at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}")

    all_articles = []
    all_articles += fetch_newsapi()
    all_articles += fetch_rss()
    all_articles += fetch_gdelt()

    unique_articles = deduplicate(all_articles)
    print(f"\nTotal unique articles fetched: {len(unique_articles)}")
    return unique_articles

if __name__ == "__main__":
    articles = fetch_all_news()
    print("\nSample articles:")
    for i, a in enumerate(articles[:5]):
        print(f"\n[{i+1}] {a['title']}")
        print(f"     Source : {a['source']}")
        print(f"     Feed   : {a['feed']}")
        print(f"     URL    : {a['url']}")