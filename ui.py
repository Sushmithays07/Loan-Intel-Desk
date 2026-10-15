"""Shared look & feel: theme CSS, sidebar navigation, header, cards, chart styling, formatters."""
from __future__ import annotations

import streamlit as st

import api_client

TEAL, GREEN, RED, BLUE = "#14B8A6", "#10D48E", "#FF4D6D", "#2F8CFF"
PURPLE, YELLOW, PINK, SKY = "#8B5CF6", "#FFD166", "#FF7EB6", "#4FC3F7"
FEATURE_COLORS = [TEAL, BLUE, PURPLE, YELLOW, SKY, PINK]

CSS = """
<style>
.stApp { background: radial-gradient(1200px 600px at 80% -10%, #0F2A44 0%, #07111F 55%); }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.6rem; max-width: 1500px; }
[data-testid="stSidebarNav"] { display: none; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0B1A2E 0%, #08121F 100%); border-right: 1px solid #16304D; }
[data-testid="stSidebar"] .block-container { padding-top: 1rem; }

.lid-brand { display:flex; gap:.7rem; align-items:center; margin: .2rem 0 1rem 0; }
.lid-brand .logo { font-size: 1.9rem; }
.lid-brand .name { font-size: 1.35rem; font-weight: 700; color:#F2F7FD; line-height:1.1; }
.lid-brand .name span { color: #14B8A6; }
.lid-brand .tag { font-size:.78rem; color:#8CA3BD; }
.lid-section { font-size:.72rem; letter-spacing:.12em; color:#6F88A6; margin: 1.1rem 0 .3rem .2rem; font-weight:600; }
[data-testid="stPageLink-NavLink"] { border-radius: 10px; padding: .55rem .8rem; color:#BFD0E3; }
[data-testid="stPageLink-NavLink"]:hover { background:#10294A; }
[data-testid="stPageLink-NavLink"][aria-current="page"] { background:#14B8A6; color:#04201C; font-weight:700; }
[data-testid="stPageLink-NavLink"][aria-current="page"] * { color:#04201C !important; }

.lid-promo { margin-top:1.4rem; padding:1rem; border-radius:16px; border:1px solid #1B3A5C;
  background: linear-gradient(160deg,#0F3550,#0A1D33); }
.lid-promo .t { font-weight:700; color:#6FE3D5; margin-bottom:.25rem; }
.lid-promo .d { color:#9DB3CC; font-size:.8rem; }
.lid-pill { display:inline-block; padding:.2rem .65rem; border-radius:999px; font-size:.74rem; font-weight:600;
  border:1px solid; margin: .15rem .3rem .15rem 0; }
.pill-ok { color:#10D48E; border-color:#10D48E55; background:#10D48E14; }
.pill-bad { color:#FF4D6D; border-color:#FF4D6D55; background:#FF4D6D14; }
.pill-info { color:#14B8A6; border-color:#14B8A655; background:#14B8A614; }

.lid-title { font-size:2.1rem; font-weight:700; color:#F2F7FD; margin:0; line-height:1.15; }
.lid-title span { color:#14C8B6; }
.lid-sub { color:#8CA3BD; margin: .15rem 0 1rem 0; }

.lid-kpi { border-radius:16px; padding:1rem 1.1rem; border:1px solid; min-height:128px; }
.lid-kpi .label { color:#B7C8DC; font-size:.9rem; display:flex; gap:.5rem; align-items:center; }
.lid-kpi .value { font-size:2.1rem; font-weight:700; color:#fff; margin:.2rem 0; }
.lid-kpi .foot { font-size:.8rem; color:#8CA3BD; }
.kpi-teal { background:linear-gradient(135deg,#0B3B46,#0A2236); border-color:#14B8A688; }
.kpi-green { background:linear-gradient(135deg,#0B3B33,#0A2236); border-color:#10D48E88; }
.kpi-red { background:linear-gradient(135deg,#40172B,#0A2236); border-color:#FF4D6D88; }
.kpi-blue { background:linear-gradient(135deg,#0F2D5C,#0A2236); border-color:#2F8CFF88; }

.lid-card-title { font-size:1.15rem; font-weight:700; color:#F2F7FD; margin-bottom:.1rem; }
.lid-card-sub { font-size:.82rem; color:#8CA3BD; margin-bottom:.6rem; }
[data-testid="stForm"] { border:1px solid #1B3350; background:#0C1C31CC; padding:1.2rem; border-radius:16px; }
div[data-testid="stVerticalBlockBorderWrapper"] { border-radius:16px; border-color:#1B3350 !important; background:#0C1C31AA; }

.stButton > button, [data-testid="stFormSubmitButton"] > button {
  background: linear-gradient(90deg,#0FB5A5,#14C8B6); color:#04201C; font-weight:700; border:none; border-radius:10px;
  padding:.6rem 1rem; }
.stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover { filter:brightness(1.1); color:#04201C; }
.stNumberInput input, .stTextInput input, .stSelectbox div[data-baseweb="select"] > div { background:#0A1A2E !important; border-color:#1B3350 !important; }

.fi-row { display:flex; align-items:center; gap:.7rem; margin:.5rem 0; font-size:.88rem; color:#CFE0F3; }
.fi-row .n { width:150px; }
.fi-row .bar { flex:1; background:#13263D; border-radius:6px; height:12px; overflow:hidden; }
.fi-row .bar > div { height:100%; border-radius:6px; }
.fi-row .p { width:52px; text-align:right; color:#9DB3CC; }

.res-card { border-radius:18px; padding:1.3rem 1.5rem; border:1px solid; }
.res-ok { background:linear-gradient(135deg,#0B3B33,#0A2236); border-color:#10D48E; }
.res-bad { background:linear-gradient(135deg,#40172B,#0A2236); border-color:#FF4D6D; }
.res-card .big { font-size:2rem; font-weight:800; }
.res-ok .big { color:#10D48E; } .res-bad .big { color:#FF4D6D; }
.res-card .ref { color:#9DB3CC; font-size:.85rem; }
.lid-note { border-left:3px solid #14B8A6; background:#0C1C31; padding:.7rem 1rem; border-radius:6px; color:#9DB3CC; font-size:.85rem; }
.lid-empty { text-align:center; padding:2.2rem 1rem; border:1px dashed #1F3C5E; border-radius:16px; color:#8CA3BD; }
</style>
"""


def _html(s: str) -> str:
    """Collapse to one line so Streamlit's markdown never treats indented HTML as a code block."""
    return " ".join(line.strip() for line in s.strip().splitlines())


def html(s: str) -> None:
    st.markdown(_html(s), unsafe_allow_html=True)


@st.cache_data(ttl=10, show_spinner=False)
def _cached_health() -> dict:
    try:
        return api_client.get_health()
    except api_client.ApiError as exc:
        return {"status": "unreachable", "error": exc.message}


def setup_page(title: str) -> None:
    """Call first on every page: page config, theme CSS, sidebar."""
    st.set_page_config(page_title=f"{title} | Loan Intel Desk", page_icon="⚡", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    with st.sidebar:
        html('<div class="lid-brand"><div class="logo">⚡</div><div><div class="name">Loan <span>Intel</span> Desk</div>'
             '<div class="tag">Smart Lending with AI</div></div></div>')
        html('<div class="lid-section">OVERVIEW</div>')
        st.page_link("app.py", label="Dashboard", icon="🏠")
        st.page_link("pages/1_Loan_Prediction.py", label="Loan Prediction", icon="📝")
        st.page_link("pages/2_Prediction_History.py", label="Prediction History", icon="🕘")
        html('<div class="lid-section">INTELLIGENCE</div>')
        st.page_link("pages/3_Analytics.py", label="Analytics", icon="📊")
        st.page_link("pages/4_Model_Insights.py", label="Model Insights", icon="🧠")
        h = _cached_health()
        if h.get("status") == "unreachable":
            pills = '<span class="lid-pill pill-bad">API offline</span>'
        else:
            pills = ('<span class="lid-pill pill-ok">API online</span>' +
                     ('<span class="lid-pill pill-ok">DB connected</span>' if h.get("database_connected")
                      else '<span class="lid-pill pill-bad">DB offline</span>') +
                     ('<span class="lid-pill pill-ok">Model loaded</span>' if h.get("model_loaded")
                      else '<span class="lid-pill pill-bad">Model missing</span>'))
        html(f'<div style="margin-top:1rem">{pills}</div>')
        html('<div class="lid-promo"><div class="t">Smarter Decisions<br>Brighter Futures</div>'
             '<div class="d">A seminar demo of an AI-assisted loan risk screen. Not a real lending decision.</div></div>')


def page_header(main: str, accent: str, subtitle: str, pill: str | None = None) -> None:
    pill_html = f'<span class="lid-pill pill-info" style="float:right">{pill}</span>' if pill else ""
    html(f'<div>{pill_html}<h1 class="lid-title">{main} <span>{accent}</span></h1><div class="lid-sub">{subtitle}</div></div>')


def kpi_card(label: str, value: str, foot: str, tone: str, icon: str) -> None:
    html(f'<div class="lid-kpi kpi-{tone}"><div class="label">{icon} {label}</div>'
         f'<div class="value">{value}</div><div class="foot">{foot}</div></div>')


def card_title(title: str, subtitle: str = "") -> None:
    html(f'<div class="lid-card-title">{title}</div><div class="lid-card-sub">{subtitle}</div>')


def empty_state(message: str, hint: str = "") -> None:
    html(f'<div class="lid-empty"><div style="font-size:2rem">🗂️</div><b>{message}</b><br>{hint}</div>')


def api_error(exc: api_client.ApiError) -> None:
    icon = {"connection": "🔌", "timeout": "⏱️", "validation": "⚠️"}.get(exc.kind, "❌")
    st.error(exc.message, icon=icon)


def feature_bars(importances: dict[str, float], top: int = 6) -> None:
    items = sorted(((k, v) for k, v in importances.items() if v > 0), key=lambda kv: -kv[1])[:top]
    rows = ""
    for i, (name, v) in enumerate(items):
        rows += (f'<div class="fi-row"><div class="n">{pretty(name)}</div><div class="bar"><div style="width:{v*100:.1f}%;'
                 f'background:{FEATURE_COLORS[i % len(FEATURE_COLORS)]}"></div></div><div class="p">{v*100:.1f}%</div></div>')
    html(rows)


def style_fig(fig, height: int = 340):
    fig.update_layout(height=height, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#CFE0F3"), margin=dict(l=10, r=10, t=30, b=10),
                      legend=dict(orientation="h", y=1.12, x=1, xanchor="right"))
    fig.update_xaxes(gridcolor="#16304D", zerolinecolor="#16304D")
    fig.update_yaxes(gridcolor="#16304D", zerolinecolor="#16304D")
    return fig


def pretty(name: str) -> str:
    special = {"dti": "Debt-to-Income Ratio", "loan_income_ratio": "Loan-to-Income Ratio",
               "savings_loan_ratio": "Savings-to-Loan Ratio", "monthly_emi": "Monthly EMI"}
    return special.get(name, name.replace("_", " ").title())


def inr(x: float | int | None) -> str:
    """Format with Indian digit grouping: 1234567 -> ₹12,34,567."""
    if x is None:
        return "-"
    s = f"{abs(round(float(x))):d}"
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups + [tail])
    return ("-" if x < 0 else "") + "₹" + s
