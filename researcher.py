from dotenv import load_dotenv
load_dotenv()

import os
import streamlit as st
if hasattr(st, "secrets"):
    for k, v in st.secrets.items():
        os.environ.setdefault(k, str(v))

import anthropic
import requests
import re
import json
import os

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL             = "claude-haiku-4-5-20251001"
MAX_TOKENS        = 1200

def _fetch_article_text(url: str, max_chars: int = 2000) -> str:
    try:
        headers = {"User-Agent": "LinkedInAgent/1.0"}
        resp    = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        text = re.sub(r"<[^>]+>", " ", resp.text)
        text = re.sub(r"\s+", " ", text).strip()
        start = max(0, len(text) // 8)
        return text[start: start + max_chars]
    except Exception as e:
        return f"Could not fetch article: {e}"

def generate_research_pack(article: dict) -> dict:
    """
    Takes an article dict (id, title, source, url, why) and returns a
    research pack dict with: summary, india_angle, data_points, angles.
    """
    snippet = _fetch_article_text(article["url"])

    style_path = os.path.join(os.path.dirname(__file__), "style_guide.txt")
    style_note = ""
    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as f:
            style_note = f.read()[:400]

    system = (
        "You are a research assistant helping an Indian marketing professional "
        "prepare to write a LinkedIn post. You do NOT write the post. "
        "You produce a structured research pack so they can form their own opinion. "
        "Reply ONLY with valid JSON — no markdown, no preamble."
    )

    user = f"""Article title: {article['title']}
Source: {article['source']}
Why it was picked: {article['why']}
Article content: {snippet}

Produce a research pack in this exact JSON format:
{{
  "summary": ["bullet 1", "bullet 2", "bullet 3", "bullet 4"],
  "india_angle": "2-3 sentences on why this specifically matters for Indian brands or consumers",
  "data_points": ["specific fact or number 1", "specific fact or number 2", "specific fact or number 3"],
  "angles": [
    {{"title": "angle title 1", "description": "one sentence on this direction"}},
    {{"title": "angle title 2", "description": "one sentence on this direction"}},
    {{"title": "angle title 3", "description": "one sentence on this direction"}}
  ]
}}

Make the angles genuinely different from each other — contrarian, strategic, personal observation."""

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        raw = resp.content[0].text.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        return {
            "summary":     ["Could not generate research pack.", str(e)],
            "india_angle": "",
            "data_points": [],
            "angles":      [],
        }

def polish_draft(draft: str, article_title: str) -> str:
    """
    Takes the user's rough draft and polishes it using their style guide.
    Preserves all ideas — only improves the writing.
    """
    style_path = os.path.join(os.path.dirname(__file__), "style_guide.txt")
    style = ""
    if os.path.exists(style_path):
        with open(style_path, "r", encoding="utf-8") as f:
            style = f.read()

    system = (
        "You are a writing editor. Your job is to improve the writing quality "
        "of a LinkedIn post draft — tighten sentences, fix flow, strengthen the hook. "
        "You MUST preserve every idea, opinion, and perspective the person has expressed. "
        "Do NOT add new ideas. Do NOT make it sound more AI-generated. "
        "Output only the final polished post — no commentary, no preamble."
        f"\n\nSTYLE GUIDE:\n{style}"
    )

    user = (
        f"Article this post is about: {article_title}\n\n"
        f"My rough draft:\n{draft}\n\n"
        "Polish this. Keep my voice and all my ideas. Just make the writing tighter and stronger."
    )

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        resp = client.messages.create(
            model=MODEL,
            max_tokens=800,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        return f"Polish failed: {e}"
