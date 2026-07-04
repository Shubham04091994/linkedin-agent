"""
fetcher.py — pulls articles from India-focused RSS feeds + Reddit
Filters by relevance keywords and returns a clean list for the curator.
"""

import feedparser
import hashlib
import time
from datetime import datetime, timezone

# ─── FEED SOURCES ────────────────────────────────────────────────────────────

FEEDS = {
    # News & media
    "Inc42":          "https://inc42.com/feed/",
    "YourStory":      "https://yourstory.com/feed/",
    "MediaNama":      "https://medianama.com/feed/",
    "Brand Equity":   "https://brandequity.economictimes.indiatimes.com/rss/topstories",
    "Campaign India": "https://www.campaignindia.in/rss.xml",
    "Adgully":        "https://www.adgully.com/feed/",
    "The Ken":        "https://the-ken.com/feed/",    
    "Entrackr":       "https://entrackr.com/feed",   # no trailing slash
    "Reddit/IndianBusiness": "https://www.reddit.com/r/IndianBusiness/.rss",
    "Reddit/India":   "https://www.reddit.com/r/india/.rss",
    "Mint News":     "https://www.livemint.com/rss/news",
    "Mint Opinion":  "https://www.livemint.com/rss/opinion",
    "Mint Industry": "https://www.livemint.com/rss/industry",
    "Mint Money":    "https://www.livemint.com/rss/money",

}

# ─── RELEVANCE KEYWORDS ───────────────────────────────────────────────────────
# Articles must match at least MIN_KEYWORD_HITS of these to pass the filter.
# Add/remove freely — these define your content niche.

KEYWORDS = [
    # D2C & brands
    "D2C", "direct-to-consumer", "brand", "brand campaign", "brand strategy",
    "boAt", "Mamaearth", "Nykaa", "Lenskart", "Boat", "MCaffeine", "Plum",
    "Sugar Cosmetics", "Minimalist", "Wow Skin", "The Whole Truth",
    # Startups & growth
    "startup", "funding", "Series A", "Series B", "unicorn", "valuation",
    "revenue", "growth", "scale", "expansion",
    # Consumer behaviour & marketing
    "consumer behaviour", "consumer behavior", "marketing", "campaign",
    "advertising", "ad spend", "media buying", "influencer", "creator economy",
    "performance marketing", "digital marketing", "social media marketing",
    # Cricket / IPL / OTT (business angle)
    "IPL", "cricket sponsorship", "OTT", "streaming", "Hotstar",
    "JioCinema", "Netflix India", "Amazon Prime India",
    # Key companies often worth tracking
    "Zomato", "Swiggy", "Zepto", "Blinkit", "Meesho", "CRED", "Razorpay",
    "PhonePe", "Paytm", "Flipkart", "Myntra", "Urban Company",
    # Sectors
    "quick commerce", "e-commerce", "fintech", "edtech", "healthtech",
    "consumer internet", "retail", "FMCG", "BFSI",
    # Broad India business
    "Indian market", "India market", "Indian consumer", "India startup",
    "India brand", "Made in India",
]

MIN_KEYWORD_HITS = 2   # raise to 2 if too many irrelevant articles slip through
MAX_ARTICLES_PER_FEED = 10  # fetch more, let the curator pick the best 5

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def _make_id(url: str) -> str:
    """Stable short ID from URL — same article always gets same ID."""
    return hashlib.md5(url.encode()).hexdigest()[:8]

def _score_article(title: str, summary: str) -> int:
    """Count how many keywords appear in title + summary (case-insensitive)."""
    text = (title + " " + summary).lower()
    return sum(1 for kw in KEYWORDS if kw.lower() in text)

def _clean_summary(raw: str, max_chars: int = 500) -> str:
    """Strip HTML tags and truncate."""
    import re
    clean = re.sub(r"<[^>]+>", "", raw or "")
    clean = " ".join(clean.split())          # collapse whitespace
    return clean[:max_chars] + "…" if len(clean) > max_chars else clean

def _parse_date(entry) -> str:
    """Best-effort published date as ISO string."""
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).isoformat()
        except Exception:
            pass
    return datetime.now(timezone.utc).isoformat()

# ─── MAIN FETCHER ─────────────────────────────────────────────────────────────

def fetch_articles(verbose: bool = False) -> list[dict]:
    """
    Fetch from all feeds, filter by keywords, deduplicate, return sorted list.

    Each article dict:
        id          — stable 8-char hash of URL
        title       — article headline
        url         — canonical link
        source      — feed name (e.g. "Inc42")
        summary     — cleaned snippet (~300 chars)
        score       — keyword hit count (higher = more relevant)
        published   — ISO datetime string
    """
    all_articles = []
    seen_ids = set()

    headers = {
        # Reddit blocks default feedparser user-agent; this fixes it
        "User-Agent": "LinkedInAgent/1.0 (personal automation; +https://github.com/you/linkedin-agent)"
    }

    for source_name, feed_url in FEEDS.items():
        if verbose:
            print(f"  Fetching {source_name}…", end=" ", flush=True)

        try:
            # feedparser doesn't pass custom headers natively for Reddit,
            # so use requests to fetch raw XML then parse.
            import requests
            resp = requests.get(feed_url, headers=headers, timeout=10)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
        except Exception as e:
            if verbose:
                print(f"SKIP ({e})")
            continue

        fetched = 0
        for entry in feed.entries[:MAX_ARTICLES_PER_FEED]:
            url   = getattr(entry, "link", None)
            title = getattr(entry, "title", "").strip()
            raw_summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
            summary = _clean_summary(raw_summary)

            if not url or not title:
                continue

            article_id = _make_id(url)
            if article_id in seen_ids:
                continue        # deduplicate across feeds
            seen_ids.add(article_id)

            score = _score_article(title, summary)
            if score < MIN_KEYWORD_HITS:
                continue        # not relevant enough

            all_articles.append({
                "id":        article_id,
                "title":     title,
                "url":       url,
                "source":    source_name,
                "summary":   summary,
                "score":     score,
                "published": _parse_date(entry),
            })
            fetched += 1

        if verbose:
            print(f"{fetched} articles kept")

        time.sleep(0.3)     # polite crawl delay

    # Sort: highest relevance score first, then newest
    all_articles.sort(key=lambda a: (-a["score"], a["published"]), reverse=False)
    all_articles.sort(key=lambda a: -a["score"])

    if verbose:
        print(f"\n✓ Total after filtering: {len(all_articles)} articles")

    return all_articles


# ─── QUICK TEST ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Fetching India-focused articles…\n")
    articles = fetch_articles(verbose=True)
    print(f"\nTop 10 by relevance score:\n{'─'*60}")
    for a in articles[:10]:
        print(f"[{a['score']:>2} hits] [{a['source']:<20}] {a['title'][:70]}")
        print(f"         {a['url'][:80]}\n")
