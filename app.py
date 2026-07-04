from dotenv import load_dotenv
load_dotenv()

import os
try:
    import streamlit as st
    # Bridge Streamlit secrets → os.environ so all modules can read them
    for key, value in st.secrets.items():
        os.environ[key] = str(value)
except Exception:
    pass  # Running locally, .env handles it

import streamlit as st
from storage    import get_todays_picks, init_db
from researcher import generate_research_pack, polish_draft
from fetcher    import fetch_articles
from curator    import curate
from storage    import save_picks

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title  = "LinkedIn Agent",
    page_icon   = "📰",
    layout      = "centered",
    initial_sidebar_state = "collapsed",
)

# ─── MINIMAL MOBILE-FRIENDLY CSS ─────────────────────────────────────────────

st.markdown("""
<style>
    .block-container { padding: 1rem 1rem 2rem; max-width: 480px; margin: auto; }
    .article-card {
        border: 0.5px solid #e0e0e0;
        border-radius: 12px;
        padding: 14px 16px;
        margin-bottom: 10px;
        cursor: pointer;
        background: white;
    }
    .source-pill {
        display: inline-block;
        font-size: 10px;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 6px;
        background: #e8f4fd;
        color: #1a6fa8;
        margin-bottom: 6px;
    }
    .section-box {
        background: #f8f9fa;
        border-radius: 10px;
        padding: 12px 14px;
        margin-bottom: 12px;
    }
    .angle-card {
        border-left: 3px solid #1a6fa8;
        padding: 8px 12px;
        margin-bottom: 8px;
        background: #f0f7ff;
        border-radius: 0 8px 8px 0;
    }
    .angle-green  { border-left-color: #2e7d32; background: #f1f8f1; }
    .angle-amber  { border-left-color: #e65100; background: #fff8f0; }
    .angle-blue   { border-left-color: #1565c0; background: #f0f4ff; }
    hr { border: none; border-top: 0.5px solid #e0e0e0; margin: 16px 0; }
</style>
""", unsafe_allow_html=True)

# ─── SESSION STATE ────────────────────────────────────────────────────────────

if "screen"         not in st.session_state: st.session_state.screen         = "digest"
if "selected"       not in st.session_state: st.session_state.selected       = None
if "research_pack"  not in st.session_state: st.session_state.research_pack  = None
if "polished_post"  not in st.session_state: st.session_state.polished_post  = None
if "picks"          not in st.session_state: st.session_state.picks          = []

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def go_to_digest():
    st.session_state.screen        = "digest"
    st.session_state.selected      = None
    st.session_state.research_pack = None
    st.session_state.polished_post = None

def select_article(pick):
    st.session_state.selected      = pick
    st.session_state.research_pack = None
    st.session_state.polished_post = None
    st.session_state.screen        = "research"

# ─── SCREEN 1: DIGEST ────────────────────────────────────────────────────────

def screen_digest():
    st.markdown("### 📰 Today's digest")

    init_db()
    picks = get_todays_picks()

    if not picks:
        st.info("No articles curated yet for today.")
        if st.button("⚡ Fetch & curate now", use_container_width=True):
            with st.spinner("Fetching articles from all sources…"):
                articles = fetch_articles()
            if not articles:
                st.error("No articles fetched. Check your internet connection.")
                return
            with st.spinner(f"Curating top 5 from {len(articles)} articles…"):
                curated = curate(articles)
            if not curated:
                st.error("Curation failed. Check your API key.")
                return
            run_date = save_picks(curated)
            for i, p in enumerate(curated, 1):
                p["run_date"]    = run_date
                p["pick_number"] = i
            st.success("Done! Your digest is ready.")
            st.rerun()
        return

    st.caption(f"{picks[0].get('run_date', 'Today')} · {len(picks)} articles")
    st.markdown("<hr>", unsafe_allow_html=True)

    for p in picks:
        with st.container():
            st.markdown(
                f'<div class="source-pill">{p["source"]}</div>',
                unsafe_allow_html=True
            )
            st.markdown(f"**{p['title']}**")
            st.caption(p.get("why", ""))
            if st.button("Research this →", key=f"pick_{p['pick_number']}",
                         use_container_width=True):
                select_article(p)
                st.rerun()
            st.markdown("<hr>", unsafe_allow_html=True)

# ─── SCREEN 2: RESEARCH PACK ─────────────────────────────────────────────────

def screen_research():
    pick = st.session_state.selected
    if not pick:
        go_to_digest()
        st.rerun()
        return

    if st.button("← Back to digest"):
        go_to_digest()
        st.rerun()

    st.markdown(f"### {pick['title']}")
    st.caption(f"{pick['source']} · [Read original]({pick['url']})")
    st.markdown("<hr>", unsafe_allow_html=True)

    # Generate research pack if not already done
    if st.session_state.research_pack is None:
        with st.spinner("Building your research pack…"):
            st.session_state.research_pack = generate_research_pack(pick)
        st.rerun()

    pack = st.session_state.research_pack

    # What happened
    st.markdown("**What happened**")
    with st.container():
        st.markdown('<div class="section-box">', unsafe_allow_html=True)
        for bullet in pack.get("summary", []):
            st.markdown(f"• {bullet}")
        st.markdown('</div>', unsafe_allow_html=True)

    # India angle
    if pack.get("india_angle"):
        st.markdown("**Why it matters for India**")
        st.markdown(
            f'<div class="section-box">{pack["india_angle"]}</div>',
            unsafe_allow_html=True
        )

    # Data points
    if pack.get("data_points"):
        st.markdown("**Numbers worth using**")
        with st.container():
            st.markdown('<div class="section-box">', unsafe_allow_html=True)
            for dp in pack["data_points"]:
                st.markdown(f"📊 {dp}")
            st.markdown('</div>', unsafe_allow_html=True)

    # Angles
    if pack.get("angles"):
        st.markdown("**3 angles you could take**")
        colors = ["angle-green", "angle-amber", "angle-blue"]
        for i, angle in enumerate(pack["angles"]):
            css = colors[i % 3]
            st.markdown(
                f'<div class="angle-card {css}">'
                f'<strong>{angle["title"]}</strong><br>'
                f'<span style="font-size:13px">{angle["description"]}</span>'
                f'</div>',
                unsafe_allow_html=True
            )

    st.markdown("<hr>", unsafe_allow_html=True)

    # Write + Polish
    st.markdown("**Write your rough take**")
    st.caption("Don't worry about quality — just write what you actually think. Even 3 sentences.")

    draft = st.text_area(
        label        = "Your draft",
        placeholder  = "e.g. What strikes me about this is… I've seen this pattern before when… My take is that Indian brands need to…",
        height       = 150,
        label_visibility = "collapsed",
    )

    if st.button("✨ Polish my draft", use_container_width=True, disabled=not draft.strip()):
        with st.spinner("Polishing your draft…"):
            st.session_state.polished_post = polish_draft(draft, pick["title"])
        st.session_state.screen = "polish"
        st.rerun()

# ─── SCREEN 3: POLISHED POST ─────────────────────────────────────────────────

def screen_polish():
    pick = st.session_state.selected

    if st.button("← Back to research"):
        st.session_state.screen        = "research"
        st.session_state.polished_post = None
        st.rerun()

    st.markdown("### Your LinkedIn post")
    st.caption("In your voice. Copy and paste to LinkedIn.")
    st.markdown("<hr>", unsafe_allow_html=True)

    post = st.session_state.polished_post or ""
    st.text_area(
        label            = "Post",
        value            = post,
        height           = 350,
        label_visibility = "collapsed",
    )

    st.button("📋 Copy to clipboard", use_container_width=True,
              on_click=lambda: st.write(""))
    st.caption("Select all text above and copy manually if the button doesn't work on mobile.")

    st.markdown("<hr>", unsafe_allow_html=True)
    if st.button("← Back to digest", use_container_width=True):
        go_to_digest()
        st.rerun()

# ─── ROUTER ───────────────────────────────────────────────────────────────────

screen = st.session_state.screen
if   screen == "digest":   screen_digest()
elif screen == "research": screen_research()
elif screen == "polish":   screen_polish()
