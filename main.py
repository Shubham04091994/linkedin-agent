"""
main.py — daily orchestrator.
Runs: fetch → curate → save → send WhatsApp digest.
Called by GitHub Actions every morning at 7am IST.
"""

from dotenv import load_dotenv
load_dotenv()

from fetcher  import fetch_articles
from curator  import curate
from storage  import save_picks, get_todays_picks
from notifier import send_digest

def run():
    print("━━━ LinkedIn Agent — Daily Run ━━━\n")

    # Step 1 — Fetch
    print("1/ Fetching articles from all sources…")
    articles = fetch_articles(verbose=True)
    if not articles:
        print("✗ No articles fetched. Check feed URLs.")
        return
    print(f"   → {len(articles)} articles after filtering\n")

    # Step 2 — Curate
    print("2/ Curating top 5 with Claude Haiku…")
    picks = curate(articles, verbose=True)
    if not picks:
        print("✗ Curation failed. Check API key.")
        return
    print(f"   → {len(picks)} picks selected\n")

    # Step 3 — Save
    print("3/ Saving to database…")
    run_date = save_picks(picks)
    # Attach run_date to each pick for the notifier
    for i, p in enumerate(picks, 1):
        p["run_date"] = run_date
        p["pick_number"] = i
    print(f"   → Saved for {run_date}\n")

    # Step 4 — Notify
    print("4/ Sending WhatsApp digest…")
    send_digest(picks, verbose=True)

    print("\n━━━ Done ━━━")
    print("To generate a post: python generator.py --pick <1-5>")

if __name__ == "__main__":
    run()
