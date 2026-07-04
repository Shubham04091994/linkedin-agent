"""
fetcher.py — pulls articles from India-focused RSS feeds + trending sources
"""

import feedparser
import hashlib
import time
import requests
import re
from datetime import datetime, timezone

FEEDS = {
    # Core India business & startup
    "Inc42":          "https://inc42.com/feed/",
    "YourStory":      "https://yourstory.com/feed/",
    "MediaNama":      "https://medianama.com/feed/",
    "The Ken":        "https://the-ken.com/feed/",

    # Mint — multiple sections
    "Mint News":      "https://www.livemint.com/rss/news",
    "Mint Opinion":   "https://www.livemint.com/rss/opinion",
    "Mint Industry":  "https://www.livemint.com/rss/industry",
    "Mint Money":     "https://www.livemint.com/rss/money",

    # Brand, marketing & advertising
    "Brand Equity":   "https://brandequity.economictimes.indiatimes.com/rss/topstories",
    "Campaign India": "https://www.campaignindia.in/rss.xml",
    "Adgully":        "https://www.adgully.com/feed/",
    "Afaqs":          "https://www.afaqs.com/rss/news.xml",

    # Sports-business & sponsorship
    "SportsPro":      "https://www.sportspromedia.com/feed/",
    "Scroll Sports":  "https://scroll.in/field/feed",

    # Trending in India right now
    "Google Trends":  "https://trends.google.com/trending/rss?geo=IN",

    # Reddit
    "Reddit/IndianBusiness": "https://www.reddit.com/r/IndianBusiness/.rss",
    "Reddit/Startups":       "https://www.reddit.com/r/startups/.rss",
}

KEYWORDS = [
    # D2C & brands
    "D2C", "direct-to-consumer", "brand", "brand campaign", "brand strategy",
    "brand activation", "brand ambassador", "brand identity",
    "boAt", "Mamaearth", "Nykaa", "Lenskart", "MCaffeine", "Plum",
    "Sugar Cosmetics", "Minimalist", "Wow Skin", "The Whole Truth",
    # Startups & growth
    "startup", "funding", "Series A", "Series B", "unicorn", "valuation",
    "revenue", "growth", "scale", "expansion", "acquisition", "merger",
    # Consumer behaviour & marketing
    "consumer behaviour", "consumer behavior", "marketing", "campaign",
    "advertising", "ad spend", "media buying", "influencer", "creator economy",
    "performance marketing", "digital marketing", "social media marketing",
    "viral", "viral campaign", "moment marketing",
    # Sports-business
    "IPL", "cricket", "FIFA", "World Cup", "sponsorship", "sports marketing",
    "jersey sponsor", "OTT", "streaming", "Hotstar", "JioCinema",
    "Netflix India", "Amazon Prime India", "broadcast rights",
    # Key companies
    "Zomato", "Swiggy", "Zepto", "Blinkit", "Meesho", "CRED", "Razorpay",
    "PhonePe", "Paytm", "Flipkart", "Myntra", "Urban Company",
    "Tata", "Reliance", "Jio",
    # Sectors
    "quick commerce", "e-commerce", "fintech", "edtech", "healthtech",
    "consumer internet", "retail", "FMCG", "BFSI",
    # India broad
    "Indian market", "India market", "Indian consumer", "India startup",
    "India brand", "Made in India", "Bharat", "tier 2", "tier 3",
]

MIN_KEYWORD_HITS = 2
MAX_ARTICLES_PER_FEED = 10

def _make_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:8]

def _score_article(title: str, summary: str) -> int:
    text = (title + " " + summary).lower()
    return sum(1 for kw in KEYWORDS if kw.lower() in text)

def _clean_summary(raw: str, max_chars: int = 500) -> str:
    clean = re.sub(r"<[^>]+>", "", raw or "")
    clean = " ".join(clean.split())
    return clean[:max_chars] + "…" if len(clean) > max_chars else clean

def _parse_date(entry) -> str:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
        except Exception:
            pass
    return datetime.now(timezone.utc).isoformat()

def fetch_articles(verbose: bool = False) -> list[dict]:
    all_articles = []
    seen_ids = set()
    headers = {"User-Agent": "LinkedInAgent/1.0 (personal automation)"}

    for source_name, feed_url in FEEDS.items():
        if verbose:
            print(f"  Fetching {source_name}…", end=" ", flush=True)
        try:
            resp = requests.get(feed_url, headers=headers, timeout=10)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
        except Exception as e:
            if verbose:
                print(f"SKIP ({e})")
            continue

        fetched = 0
        for entry in feed.entries[:MAX_ARTICLES_PER_FEED]:
            url     = getattr(entry, "link", None)
            title   = getattr(entry, "title", "").strip()
            raw_sum = getattr(entry, "summary", "") or getattr(entry, "description", "")
            summary = _clean_summary(raw_sum)

            if not url or not title:
                continue

            article_id = _make_id(url)
            if article_id in seen_ids:
                continue
            seen_ids.add(article_id)

            is_trends = source_name == "Google Trends"
            score = _score_article(title, summary)
            if not is_trends and score < MIN_KEYWORD_HITS:
                continue

            all_articles.append({
                "id": article_id, "title": title, "url": url,
                "source": source_name, "summary": summary,
                "score": score, "published": _parse_date(entry),
            })
            fetched += 1

        if verbose:
            print(f"{fetched} articles kept")
        time.sleep(0.3)

    all_articles.sort(key=lambda a: -a["score"])
    if verbose:
        print(f"\n✓ Total after filtering: {len(all_articles)} articles")
    return all_articles

if __name__ == "__main__":
    print("Fetching articles…\n")
    articles = fetch_articles(verbose=True)
    print(f"\nTop 10 by relevance score:\n{'─'*60}")
    for a in articles[:10]:
        print(f"[{a['score']:>2} hits] [{a['source']:<22}] {a['title'][:65]}")
        print(f"         {a['url'][:80]}\n")