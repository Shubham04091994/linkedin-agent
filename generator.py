"""
generator.py — takes a selected article (by pick number 1-5) and drafts
a LinkedIn post using Claude Haiku + your personal style guide.
Usage: python generator.py --pick 3
"""

from dotenv import load_dotenv
load_dotenv()

import anthropic
import argparse
import os
import requests
from storage import get_pick_by_number, mark_as_used

# ─── CONFIG ──────────────────────────────────────────────────────────────────

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL             = "claude-haiku-4-5"
MAX_TOKENS        = 800
STYLE_GUIDE_PATH  = os.path.join(os.path.dirname(__file__), "style_guide.txt")

# ─── LOAD STYLE GUIDE ────────────────────────────────────────────────────────

def _load_style_guide() -> str:
    if not os.path.exists(STYLE_GUIDE_PATH):
        return (
            "Write in a conversational, human tone. "
            "No corporate jargon. Short punchy sentences. "
            "Start with a strong hook. End with a question to drive comments. "
            "No hashtag spam — max 3 relevant hashtags."
        )
    with open(STYLE_GUIDE_PATH, "r", encoding="utf-8") as f:
        return f.read().strip()

# ─── FETCH ARTICLE TEXT ──────────────────────────────────────────────────────

def _fetch_article_snippet(url: str, max_chars: int = 1500) -> str:
    """
    Fetch a short snippet of the article to give Claude context.
    We cap at 1500 chars to keep tokens low.
    """
    try:
        headers = {"User-Agent": "LinkedInAgent/1.0"}
        resp = requests.get(url, headers=headers, timeout=8)
        resp.raise_for_status()

        # Strip HTML tags simply
        import re
        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s+", " ", text).strip()

        # Find the main content area (rough heuristic — skip nav/header noise)
        start = max(0, len(text) // 6)
        snippet = text[start: start + max_chars]
        return snippet
    except Exception as e:
        return f"[Could not fetch article content: {e}]"

# ─── MAIN GENERATOR ──────────────────────────────────────────────────────────

def generate_post(pick_number: int, verbose: bool = False) -> str:
    """
    Generates a LinkedIn post draft for the selected article.
    Returns the post text as a string.
    """
    pick = get_pick_by_number(pick_number)
    if not pick:
        return f"❌ No article found for pick #{pick_number} today. Run main.py first."

    style_guide = _load_style_guide()

    if verbose:
        print(f"  Article: {pick['title']}")
        print(f"  Source:  {pick['source']}")
        print(f"  Fetching article content…")

    snippet = _fetch_article_snippet(pick["url"])

    system_prompt = (
        "You are a LinkedIn ghostwriter. "
        "Write exactly ONE LinkedIn post — no explanations, no options, no preamble. "
        "Just the post itself, ready to copy-paste.\n\n"
        f"STYLE GUIDE:\n{style_guide}"
    )

    user_prompt = (
        f"Write a LinkedIn post based on this article.\n\n"
        f"Title: {pick['title']}\n"
        f"Source: {pick['source']}\n"
        f"Why it matters: {pick['why']}\n\n"
        f"Article snippet:\n{snippet}\n\n"
        "Write the post now. Start directly with the hook — no intro text."
    )

    if verbose:
        print("  Drafting post with Claude Haiku…")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )

    post_text = response.content[0].text.strip()

    usage = response.usage
    if verbose:
        print(f"  Tokens — input: {usage.input_tokens}, output: {usage.output_tokens}")

    # Mark article as used so you don't accidentally reuse it
    mark_as_used(pick["run_date"], pick_number)

    return post_text


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a LinkedIn post from today's picks.")
    parser.add_argument("--pick", type=int, required=True, choices=[1, 2, 3, 4, 5],
                        help="Which article to use (1-5)")
    args = parser.parse_args()

    print(f"\nGenerating LinkedIn post for pick #{args.pick}…\n")
    post = generate_post(args.pick, verbose=True)

    print("\n" + "─" * 60)
    print("YOUR LINKEDIN POST — COPY EVERYTHING BELOW THIS LINE")
    print("─" * 60)
    print(post)
    print("─" * 60)
