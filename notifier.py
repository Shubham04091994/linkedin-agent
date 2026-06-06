"""
notifier.py — sends the daily top 5 digest to your WhatsApp via Twilio.
Reuses the same Twilio sandbox you already have from the food scanner.
"""

from dotenv import load_dotenv
load_dotenv()

import os
from twilio.rest import Client

# ─── CONFIG ──────────────────────────────────────────────────────────────────

TWILIO_SID   = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
FROM_WHATSAPP = "whatsapp:+14155238886"          # Twilio sandbox number
TO_WHATSAPP   = os.environ.get("MY_WHATSAPP", "") # your number e.g. whatsapp:+919999999999

# ─── FORMATTER ───────────────────────────────────────────────────────────────

def _format_digest(picks: list[dict]) -> str:
    today = picks[0].get("run_date", "Today") if picks else "Today"
    lines = [f"📰 *LinkedIn Digest — {today}*\n"]
    for p in picks:
        n     = p["pick_number"]
        src   = p["source"]
        title = p["title"][:60]
        url   = p["url"]
        lines.append(f"*{n}.* [{src}] {title}\n{url}\n")
    lines.append("▶ To draft a post:\n`python generator.py --pick <1-5>`")
    return "\n".join(lines)

# ─── SENDER ──────────────────────────────────────────────────────────────────

def send_digest(picks: list[dict], verbose: bool = False) -> bool:
    """Send today's picks to WhatsApp. Returns True if successful."""
    if not all([TWILIO_SID, TWILIO_TOKEN, TO_WHATSAPP]):
        print("⚠️  Twilio credentials not set — skipping WhatsApp notification.")
        print("    Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, MY_WHATSAPP in .env")
        return False

    message_body = _format_digest(picks)

    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        msg = client.messages.create(
            body=message_body,
            from_=FROM_WHATSAPP,
            to=TO_WHATSAPP,
        )
        if verbose:
            print(f"  ✓ WhatsApp sent — SID: {msg.sid}")
        return True
    except Exception as e:
        print(f"  ✗ WhatsApp send failed: {e}")
        return False


# ─── QUICK TEST ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from storage import get_todays_picks
    picks = get_todays_picks()
    if not picks:
        print("No picks saved yet — run main.py first.")
    else:
        print("Sending digest to WhatsApp…")
        send_digest(picks, verbose=True)
