"""
Shared UI helpers for the Personal Finance Tracker.

Theme system: call inject_css() at the top of every page (as before).
It reads st.session_state["pft_theme"] ("dark" or "light", defaults to
"dark") and injects the matching CSS variables. Call theme_toggle() in
your sidebar (once, e.g. in app.py) to let the user switch — the choice
is stored in session_state so it persists across page navigation within
a session (Streamlit session_state does NOT persist across browser
restarts; add your own persistence if you need that).
"""

import streamlit as st


# ==================================================
# CATEGORIES & COLORS
# ==================================================
# NOTE: These are placeholder values reconstructed after the original
# utils.py was overwritten. Please check these against what you actually
# use in your transaction forms / budget categories and edit as needed —
# if your category names don't match exactly, old transactions in your
# database may not match up with these lists in dropdowns/filters.

INCOME_CATEGORIES = [
    "Salary",
    "Freelance",
    "Investments",
    "Gifts",
    "Other Income",
]

EXPENSE_CATEGORIES = [
    "Food",
    "Bills",
    "Travel",
    "Rent",
    "Shopping",
    "Entertainment",
    "Healthcare",
    "Education",
    "Other Expense",
]

FINANCE_COLORS = {
    "income": "#00d4aa",
    "expense": "#fb7185",
    "balance": "#7c5cff",
    "warning": "#fbbf24",
    "neutral": "#9aa0ac",
}

# List form for use with plotly's color_discrete_sequence (which needs
# a list, not a dict). Keep FINANCE_COLORS above for semantic lookups
# like FINANCE_COLORS["income"].
FINANCE_COLOR_SEQUENCE = list(FINANCE_COLORS.values())


# ==================================================
# FORMATTING HELPERS
# ==================================================

def format_currency(amount) -> str:
    """Format a number as 'Rs. 1,234.56'. Used across the transaction,
    budget, dashboard, and analytics pages."""
    try:
        return f"Rs. {amount:,.2f}"
    except (TypeError, ValueError):
        return "Rs. 0.00"


# ==================================================
# THEME — Light / Dark via CSS variables
# ==================================================

def _current_theme() -> str:
    return st.session_state.get("pft_theme", "dark")


def theme_toggle():
    """
    Renders a small toggle button. Place this once in your sidebar,
    e.g. in app.py:

        from utils import theme_toggle
        with st.sidebar:
            theme_toggle()
    """
    if "pft_theme" not in st.session_state:
        st.session_state.pft_theme = "dark"

    current = st.session_state.pft_theme
    label = "☀️ Light mode" if current == "dark" else "🌙 Dark mode"

    if st.button(label, key="pft_theme_toggle", use_container_width=True):
        st.session_state.pft_theme = "light" if current == "dark" else "dark"
        st.rerun()


def inject_css():
    theme = _current_theme()

    if theme == "light":
        vars_css = """
            --pft-bg: #f5f6fa;
            --pft-bg-glow-1: rgba(124, 92, 255, 0.08);
            --pft-bg-glow-2: rgba(0, 170, 140, 0.07);
            --pft-sidebar-bg: rgba(255, 255, 255, 0.75);
            --pft-sidebar-border: rgba(15, 20, 30, 0.08);
            --pft-text-primary: #1a1d24;
            --pft-text-secondary: #5b606c;
            --pft-glass-bg: rgba(15, 20, 30, 0.035);
            --pft-glass-border: rgba(15, 20, 30, 0.10);
            --pft-glass-border-hover: rgba(124, 92, 255, 0.45);
            --pft-shadow: 0 4px 20px rgba(15, 20, 30, 0.08);
            --pft-header-grad: linear-gradient(135deg, rgba(124, 92, 255, 0.10), rgba(0, 170, 140, 0.06));
            --pft-title-grad: linear-gradient(90deg, #1a1d24, #6a4fe0);
            --pft-divider-grad: linear-gradient(90deg, transparent, rgba(15,20,30,0.15), transparent);
            --pft-input-bg: rgba(15, 20, 30, 0.03);
            --pft-input-border: rgba(15, 20, 30, 0.14);
            --pft-scrollbar: rgba(15, 20, 30, 0.18);
            --pft-btn-bg: rgba(15, 20, 30, 0.04);
            --pft-btn-border: rgba(15, 20, 30, 0.12);
        """
    else:
        vars_css = """
            --pft-bg: #0b0e14;
            --pft-bg-glow-1: rgba(124, 92, 255, 0.12);
            --pft-bg-glow-2: rgba(0, 212, 170, 0.10);
            --pft-sidebar-bg: rgba(18, 21, 30, 0.85);
            --pft-sidebar-border: rgba(255, 255, 255, 0.06);
            --pft-text-primary: #f4f5f7;
            --pft-text-secondary: #9aa0ac;
            --pft-glass-bg: rgba(255, 255, 255, 0.04);
            --pft-glass-border: rgba(255, 255, 255, 0.08);
            --pft-glass-border-hover: rgba(124, 92, 255, 0.40);
            --pft-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
            --pft-header-grad: linear-gradient(135deg, rgba(124, 92, 255, 0.15), rgba(0, 212, 170, 0.08));
            --pft-title-grad: linear-gradient(90deg, #ffffff, #b9b3ff);
            --pft-divider-grad: linear-gradient(90deg, transparent, rgba(255,255,255,0.15), transparent);
            --pft-input-bg: rgba(255, 255, 255, 0.04);
            --pft-input-border: rgba(255, 255, 255, 0.1);
            --pft-scrollbar: rgba(255, 255, 255, 0.15);
            --pft-btn-bg: rgba(255, 255, 255, 0.05);
            --pft-btn-border: rgba(255, 255, 255, 0.1);
        """

    st.markdown(
        f"""
        <style>

        :root {{
            {vars_css}
        }}

        /* ---------- Base ---------- */
        html, body, [class*="css"] {{
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }}

        .stApp {{
            background:
                radial-gradient(circle at 15% 10%, var(--pft-bg-glow-1), transparent 40%),
                radial-gradient(circle at 85% 0%, var(--pft-bg-glow-2), transparent 40%),
                var(--pft-bg);
        }}

        /* ---------- Sidebar ---------- */
        section[data-testid="stSidebar"] {{
            background: var(--pft-sidebar-bg);
            backdrop-filter: blur(14px);
            border-right: 1px solid var(--pft-sidebar-border);
        }}
        section[data-testid="stSidebar"] .stMarkdown,
        section[data-testid="stSidebar"] a {{
            color: var(--pft-text-secondary) !important;
        }}

        /* ---------- Body text ---------- */
        p, span, label, li, .stMarkdown {{
            color: var(--pft-text-primary);
        }}

        /* ---------- Headings ---------- */
        h1, h2, h3 {{
            color: var(--pft-text-primary) !important;
            font-weight: 700 !important;
            letter-spacing: -0.02em;
        }}

        /* ---------- Page header block ---------- */
        .pft-header {{
            padding: 28px 32px;
            margin-bottom: 20px;
            border-radius: 20px;
            background: var(--pft-header-grad);
            border: 1px solid var(--pft-glass-border);
            backdrop-filter: blur(12px);
            box-shadow: var(--pft-shadow);
        }}
        .pft-header h1 {{
            margin: 0 0 6px 0;
            font-size: 28px;
            background: var(--pft-title-grad);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .pft-header p {{
            margin: 0;
            color: var(--pft-text-secondary);
            font-size: 15px;
        }}

        /* ---------- Section divider ---------- */
        .pft-divider {{
            height: 1px;
            margin: 28px 0;
            background: var(--pft-divider-grad);
            border: none;
        }}

        /* ---------- Generic glass card ---------- */
        .pft-card {{
            padding: 20px 22px;
            border-radius: 16px;
            background: var(--pft-glass-bg);
            border: 1px solid var(--pft-glass-border);
            backdrop-filter: blur(10px);
            box-shadow: var(--pft-shadow);
            transition: transform 0.15s ease, border-color 0.15s ease;
        }}
        .pft-card:hover {{
            transform: translateY(-2px);
            border-color: var(--pft-glass-border-hover);
        }}

        /* ---------- Metric cards ---------- */
        .pft-metric {{
            padding: 18px 20px;
            border-radius: 16px;
            background: var(--pft-glass-bg);
            border: 1px solid var(--pft-glass-border);
            backdrop-filter: blur(10px);
        }}
        .pft-metric .label {{
            font-size: 13px;
            color: var(--pft-text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 6px;
        }}
        .pft-metric .value {{
            font-size: 26px;
            font-weight: 700;
            color: var(--pft-text-primary);
        }}
        .pft-metric .delta-pos {{ color: #22c55e; font-size: 13px; margin-top: 4px; }}
        .pft-metric .delta-neg {{ color: #ef4444; font-size: 13px; margin-top: 4px; }}

        /* accent border variants */
        .pft-metric.accent-violet {{ border-top: 3px solid #7c5cff; }}
        .pft-metric.accent-teal   {{ border-top: 3px solid #00b894; }}
        .pft-metric.accent-amber  {{ border-top: 3px solid #f59e0b; }}
        .pft-metric.accent-rose   {{ border-top: 3px solid #fb7185; }}

        /* ---------- Badges ---------- */
        .pft-badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 999px;
            font-size: 12px;
            font-weight: 600;
        }}
        .pft-badge-green  {{ background: rgba(34, 197, 94, 0.15); color: #16a34a; }}
        .pft-badge-red    {{ background: rgba(239, 68, 68, 0.15); color: #dc2626; }}
        .pft-badge-violet {{ background: rgba(124, 92, 255, 0.15); color: #7c5cff; }}

        /* ---------- AI disclaimer box (Advisor page) ---------- */
        .ai-disclaimer {{
            padding: 14px 18px;
            border-radius: 14px;
            background: rgba(124, 92, 255, 0.08);
            border: 1px solid rgba(124, 92, 255, 0.25);
            color: var(--pft-text-secondary);
            font-size: 14px;
            line-height: 1.5;
            margin-bottom: 18px;
        }}

        /* ---------- Buttons ---------- */
        .stButton > button {{
            border-radius: 12px !important;
            border: 1px solid var(--pft-btn-border) !important;
            background: var(--pft-btn-bg) !important;
            color: var(--pft-text-primary) !important;
            font-weight: 600 !important;
            transition: all 0.15s ease !important;
        }}
        .stButton > button:hover {{
            border-color: #7c5cff !important;
            background: rgba(124, 92, 255, 0.15) !important;
            color: #7c5cff !important;
        }}
        .stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, #7c5cff, #00b894) !important;
            border: none !important;
            color: #ffffff !important;
        }}

        /* ---------- Inputs ---------- */
        .stTextInput input, .stNumberInput input, .stDateInput input,
        .stSelectbox > div > div, textarea {{
            background: var(--pft-input-bg) !important;
            border: 1px solid var(--pft-input-border) !important;
            border-radius: 10px !important;
            color: var(--pft-text-primary) !important;
        }}

        /* ---------- Chat bubbles ---------- */
        [data-testid="stChatMessage"] {{
            border-radius: 16px;
            padding: 4px 6px;
            margin-bottom: 4px;
        }}

        /* ---------- Dataframes / tables ---------- */
        [data-testid="stDataFrame"] {{
            border-radius: 14px;
            overflow: hidden;
            border: 1px solid var(--pft-glass-border);
        }}

        /* ---------- Expander ---------- */
        .streamlit-expanderHeader {{
            background: var(--pft-glass-bg) !important;
            border-radius: 10px !important;
        }}

        /* ---------- Scrollbar ---------- */
        ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: var(--pft-scrollbar); border-radius: 8px; }}

        </style>
        """,
        unsafe_allow_html=True,
    )


# ==================================================
# COMPONENTS
# ==================================================

def page_header(title: str, subtitle: str = ""):
    """Glass-card style page header. Same signature as before."""
    st.markdown(
        f"""
        <div class="pft-header">
            <h1>{title}</h1>
            {f'<p>{subtitle}</p>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_divider():
    """Subtle gradient divider. Same signature as before."""
    st.markdown('<hr class="pft-divider" />', unsafe_allow_html=True)


def metric_card(label: str, value: str, delta: str = None, accent: str = "violet"):
    """
    Glass metric card, nicer than st.metric for this theme.

    accent: "violet" | "teal" | "amber" | "rose"
    delta: pass a string like "+12.4%" (auto colored green) or "-3.1%" (auto red)
    """
    delta_html = ""
    if delta is not None:
        cls = "delta-neg" if delta.strip().startswith("-") else "delta-pos"
        delta_html = f'<div class="{cls}">{delta}</div>'

    st.markdown(
        f"""
        <div class="pft-metric accent-{accent}">
            <div class="label">{label}</div>
            <div class="value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def badge(text: str, kind: str = "violet"):
    """Small pill badge. kind: 'green' | 'red' | 'violet'."""
    st.markdown(f'<span class="pft-badge pft-badge-{kind}">{text}</span>', unsafe_allow_html=True)


def card_start():
    """Open a glass card container — pair with card_end() around any content."""
    st.markdown('<div class="pft-card">', unsafe_allow_html=True)


def card_end():
    st.markdown("</div>", unsafe_allow_html=True)