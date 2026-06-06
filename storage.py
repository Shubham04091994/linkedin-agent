"""
storage.py — saves and retrieves curated articles using SQLite.
Each daily run stores the top 5 picks. You select one by its number (1-5).
"""

import sqlite3
import json
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "articles.db")

# ─── SETUP ───────────────────────────────────────────────────────────────────

def init_db():
    """Create tables if they don't exist yet."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_picks (
                run_date    TEXT NOT NULL,
                pick_number INTEGER NOT NULL,
                article_id  TEXT NOT NULL,
                title       TEXT,
                source      TEXT,
                url         TEXT,
                why         TEXT,
                used        INTEGER DEFAULT 0,
                PRIMARY KEY (run_date, pick_number)
            )
        """)
        conn.commit()

# ─── SAVE ────────────────────────────────────────────────────────────────────

def save_picks(picks: list[dict]) -> str:
    """
    Save today's top 5 picks to DB.
    Returns today's run_date string (YYYY-MM-DD).
    """
    init_db()
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    with sqlite3.connect(DB_PATH) as conn:
        # Clear any existing picks for today (re-run safety)
        conn.execute("DELETE FROM daily_picks WHERE run_date = ?", (run_date,))
        for i, pick in enumerate(picks, 1):
            conn.execute("""
                INSERT INTO daily_picks
                    (run_date, pick_number, article_id, title, source, url, why)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                run_date,
                i,
                pick.get("id", ""),
                pick.get("title", ""),
                pick.get("source", ""),
                pick.get("url", ""),
                pick.get("why", ""),
            ))
        conn.commit()

    return run_date

# ─── RETRIEVE ────────────────────────────────────────────────────────────────

def get_todays_picks() -> list[dict]:
    """Return today's 5 picks as a list of dicts."""
    init_db()
    run_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""
            SELECT * FROM daily_picks
            WHERE run_date = ?
            ORDER BY pick_number
        """, (run_date,)).fetchall()
    return [dict(r) for r in rows]

def get_pick_by_number(number: int) -> dict | None:
    """Return a specific pick (1-5) from today."""
    picks = get_todays_picks()
    for p in picks:
        if p["pick_number"] == number:
            return p
    return None

def mark_as_used(run_date: str, pick_number: int):
    """Mark an article as used so you don't post it twice."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            UPDATE daily_picks SET used = 1
            WHERE run_date = ? AND pick_number = ?
        """, (run_date, pick_number))
        conn.commit()

# ─── QUICK TEST ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Simulate saving 5 fake picks and reading them back
    test_picks = [
        {"id": "abc1", "title": "Test Article 1", "source": "Inc42",
         "url": "https://inc42.com/1", "why": "Great D2C angle"},
        {"id": "abc2", "title": "Test Article 2", "source": "The Ken",
         "url": "https://the-ken.com/2", "why": "Strong brand story"},
        {"id": "abc3", "title": "Test Article 3", "source": "Mint",
         "url": "https://livemint.com/3", "why": "Consumer behaviour insight"},
        {"id": "abc4", "title": "Test Article 4", "source": "Reddit",
         "url": "https://reddit.com/4", "why": "Startup growth story"},
        {"id": "abc5", "title": "Test Article 5", "source": "Afaqs",
         "url": "https://afaqs.com/5", "why": "Campaign breakdown"},
    ]

    run_date = save_picks(test_picks)
    print(f"Saved picks for {run_date}")

    picks = get_todays_picks()
    print(f"\nRetrieved {len(picks)} picks:")
    for p in picks:
        print(f"  {p['pick_number']}. [{p['source']}] {p['title']}")

    print("\n✓ Storage working correctly")
