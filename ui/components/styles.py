"""
LocalForge — Global CSS Stilleri
Tüm sayfalarda inject edilir.
"""

import streamlit as st

FORGE_CSS = """
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Renk Değişkenleri ── */
:root {
    --forge-bg:        #0c0c0f;
    --forge-surface:   #16161d;
    --forge-surface2:  #1e1e28;
    --forge-border:    #2a2a38;
    --forge-orange:    #f97316;
    --forge-orange-dim:#7c3a12;
    --forge-blue:      #3b82f6;
    --forge-green:     #22c55e;
    --forge-red:       #ef4444;
    --forge-text:      #e2e2e8;
    --forge-muted:     #6b6b80;
    --forge-code-bg:   #111118;
}

/* ── Temel Font ── */
html, body, [class*="css"] {
    font-family: 'JetBrains Mono', monospace !important;
}

h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
    font-family: 'Syne', sans-serif !important;
    letter-spacing: -0.02em;
}

/* ── Ana Başlık Stili ── */
.stMarkdown h1 {
    font-size: 2rem !important;
    font-weight: 800 !important;
    background: linear-gradient(135deg, #f97316, #fb923c, #fbbf24);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 0 !important;
}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: var(--forge-surface) !important;
    border-right: 1px solid var(--forge-border) !important;
}

section[data-testid="stSidebar"] .stMarkdown h1 {
    font-size: 1.4rem !important;
}

/* ── Butonlar ── */
.stButton > button {
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em;
    border-radius: 6px !important;
    border: 1px solid var(--forge-border) !important;
    transition: all 0.15s ease !important;
}

.stButton > button[kind="primary"] {
    background: var(--forge-orange) !important;
    border-color: var(--forge-orange) !important;
    color: #000 !important;
    font-weight: 700 !important;
}

.stButton > button[kind="primary"]:hover {
    background: #fb923c !important;
    border-color: #fb923c !important;
    box-shadow: 0 0 20px rgba(249,115,22,0.4) !important;
    transform: translateY(-1px);
}

.stButton > button:not([kind="primary"]):hover {
    border-color: var(--forge-orange) !important;
    color: var(--forge-orange) !important;
    transform: translateY(-1px);
}

/* ── Metrikler ── */
[data-testid="metric-container"] {
    background: var(--forge-surface2) !important;
    border: 1px solid var(--forge-border) !important;
    border-radius: 8px !important;
    padding: 16px !important;
}

[data-testid="metric-container"] label {
    color: var(--forge-muted) !important;
    font-size: 0.75rem !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: var(--forge-text) !important;
    font-size: 1.6rem !important;
    font-weight: 700 !important;
}

/* ── Progress Bar ── */
.stProgress > div > div {
    background: linear-gradient(90deg, #f97316, #fbbf24) !important;
    border-radius: 4px !important;
}

.stProgress > div {
    background: var(--forge-surface2) !important;
    border-radius: 4px !important;
}

/* ── Text Input ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: var(--forge-surface2) !important;
    border: 1px solid var(--forge-border) !important;
    border-radius: 6px !important;
    color: var(--forge-text) !important;
    font-family: 'JetBrains Mono', monospace !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: var(--forge-orange) !important;
    box-shadow: 0 0 0 2px rgba(249,115,22,0.2) !important;
}

/* ── Selectbox ── */
.stSelectbox > div > div {
    background: var(--forge-surface2) !important;
    border: 1px solid var(--forge-border) !important;
    border-radius: 6px !important;
}

/* ── Radio ── */
.stRadio > div {
    gap: 8px;
}

.stRadio > div > label {
    background: var(--forge-surface2) !important;
    border: 1px solid var(--forge-border) !important;
    border-radius: 6px !important;
    padding: 10px 14px !important;
    transition: all 0.15s ease !important;
    cursor: pointer;
}

.stRadio > div > label:hover {
    border-color: var(--forge-orange) !important;
}

/* ── Kod Blokları ── */
.stCodeBlock {
    border: 1px solid var(--forge-border) !important;
    border-radius: 8px !important;
}

.stCodeBlock code {
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.82rem !important;
}

/* ── Alert / Info / Success ── */
.stAlert {
    border-radius: 8px !important;
    border-left-width: 4px !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    background: var(--forge-surface2) !important;
    border: 1px solid var(--forge-border) !important;
    border-radius: 6px !important;
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
}

/* ── Divider ── */
hr {
    border-color: var(--forge-border) !important;
    margin: 16px 0 !important;
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--forge-surface) !important;
    border-bottom: 1px solid var(--forge-border) !important;
    gap: 4px;
}

.stTabs [data-baseweb="tab"] {
    font-family: 'Syne', sans-serif !important;
    font-weight: 600 !important;
    color: var(--forge-muted) !important;
    padding: 10px 20px !important;
    border-radius: 6px 6px 0 0 !important;
}

.stTabs [aria-selected="true"] {
    color: var(--forge-orange) !important;
    border-bottom: 2px solid var(--forge-orange) !important;
    background: var(--forge-surface2) !important;
}

/* ── Toggle ── */
.stToggle label {
    font-family: 'JetBrains Mono', monospace !important;
}

/* ── Caption ── */
.stCaption {
    color: var(--forge-muted) !important;
    font-size: 0.78rem !important;
}

/* ── Forge Badge ── */
.forge-badge {
    display: inline-block;
    background: var(--forge-orange-dim);
    color: var(--forge-orange);
    padding: 2px 10px;
    border-radius: 100px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    border: 1px solid var(--forge-orange-dim);
}

/* ── Status Card ── */
.forge-status-card {
    background: var(--forge-surface2);
    border: 1px solid var(--forge-border);
    border-radius: 10px;
    padding: 16px 20px;
    margin: 8px 0;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--forge-surface); }
::-webkit-scrollbar-thumb {
    background: var(--forge-border);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover { background: var(--forge-orange); }

/* ── Sayfa Geçiş Animasyonu ── */
.main .block-container {
    animation: fadeUp 0.25s ease-out;
}

@keyframes fadeUp {
    from { opacity: 0; transform: translateY(8px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* ── Spinner ── */
.stSpinner > div {
    border-top-color: var(--forge-orange) !important;
}
</style>
"""


def inject_styles():
    """Tüm sayfalarda çağrılır — global CSS'i inject eder."""
    st.markdown(FORGE_CSS, unsafe_allow_html=True)


def forge_header(title: str, subtitle: str = "", badge: str = ""):
    """Sayfa başlığı bileşeni."""
    badge_html = f'<span class="forge-badge">{badge}</span>' if badge else ""
    st.markdown(
        f"""
    <div style="margin-bottom: 8px;">
        {badge_html}
        <h1 style="margin: 4px 0 2px 0;">{title}</h1>
        <p style="color: #6b6b80; font-size: 0.85rem; margin: 0;">{subtitle}</p>
    </div>
    """,
        unsafe_allow_html=True,
    )


def forge_card(content: str, color: str = "#2a2a38"):
    """Renkli kenarlıklı kart."""
    st.markdown(
        f"""
    <div style="
        background: #16161d;
        border: 1px solid {color};
        border-left: 3px solid {color};
        border-radius: 8px;
        padding: 14px 18px;
        margin: 8px 0;
    ">{content}</div>
    """,
        unsafe_allow_html=True,
    )


def forge_task_item(name: str, done: bool, active: bool = False):
    """Görev listesi öğesi."""
    if done:
        icon = "✅"
        style = "color: #22c55e; text-decoration: line-through; opacity: 0.7;"
    elif active:
        icon = "⚡"
        style = "color: #f97316; font-weight: 700;"
    else:
        icon = "○"
        style = "color: #6b6b80;"

    st.markdown(
        f'<div style="{style} font-size:0.88rem; padding: 3px 0;">{icon} {name}</div>',
        unsafe_allow_html=True,
    )
