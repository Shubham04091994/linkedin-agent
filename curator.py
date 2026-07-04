from dotenv import load_dotenv
load_dotenv()

import anthropic
import json
import os

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL             = "claude-haiku-4-5-20251001"
MAX_TOKENS        = 600

NICHE = (
    "Indian D2C brands, startup growth, consumer behaviour, "
    "brand campaigns, marketing strategy, cricket/IPL/OTT business angles. "
    "Audience: Indian marketing & business professionals on LinkedIn."
)

SYSTEM_PROMPT = (
    "You are a strict LinkedIn content curator for an Indian marketing/business professional. "
    "REJECT pure news announcements (funding rounds, appointments, routine launches) unless "
    "they carry a clear strategic or analytical angle. "
    "PRIORITISE: opinion pieces, strategic analysis, contrarian takes, case studies with "
    "specific numbers, and stories revealing a non-obvious pattern in Indian business/marketing. "
    "A good pick lets the reader form an opinion. A bad pick is just an FYI. "
    "Reply ONLY with valid JSON — no markdown, no preamble."
)

def _build_user_prompt(articles):
    lines = []
    for a in articles:
        summary_short = a["summary"][:400].replace("\n", " ")
        lines.append(f'[{a["id"]}] {a["source"]} | {a["title"]} | {summary_short}')
    articles_text = "\n".join(lines)
    return (
        f"Niche: {NICHE}\n\n"
        f"Articles:\n{articles_text}\n\n"
        "Return JSON in exactly this format:\n"
        '{"picks": ['
        '{"id": "...", "title": "...", "source": "...", "url": "...", "why": "one sentence"}'
        " ... (5 items)"
        "]}"
    )

def curate(articles, verbose=False):
    if not articles:
        print("No articles to curate.")
        return []

    if not ANTHROPIC_API_KEY:
        print("✗ ANTHROPIC_API_KEY not set.")
        return []

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = _build_user_prompt(articles)

    if verbose:
        print(f"  Sending {len(articles)} articles to Claude Haiku...")

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()

        usage = response.usage
        if verbose:
            print(f"  Tokens used — input: {usage.input_tokens}, output: {usage.output_tokens}")

        data  = json.loads(raw)
        picks = data.get("picks", [])
        url_map = {a["id"]: a["url"] for a in articles}
        for p in picks:
            p["url"] = url_map.get(p["id"], p.get("url", ""))
        return picks[:5]

    except Exception as e:
        print(f"  ✗ API call failed: {e}")
        return []

if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from fetcher import fetch_articles

    print("Step 1 — Fetching articles...")
    articles = fetch_articles(verbose=True)

    print("\nStep 2 — Curating top 5 with Claude Haiku...")
    picks = curate(articles, verbose=True)

    print("\n── YOUR TOP 5 FOR TODAY ──────────────────────────────────")
    for i, p in enumerate(picks, 1):
        print(f"\n{i}. [{p['source']}] {p['title']}")
        print(f"   WHY: {p['why']}")
        print(f"   URL: {p['url']}")
        print(f"   ID:  {p['id']}")
