import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Optional
import pandas as pd

# ====== THEME ======
_THEME = {
    "accent": "#2563eb",     # albastru implicit
    "font": "#111827",
    "muted": "#6b7280",
    "paper": "rgba(0,0,0,0)",
    "plot": "rgba(0,0,0,0)",
    "card_border": "#94a3b8",
}

def set_theme(accent: str = "#2563eb", font: str = "#111827", card_border: str = "#94a3b8"):
    _THEME["accent"] = accent
    _THEME["font"] = font
    _THEME["card_border"] = card_border

# ====== CARD / KPI helpers ======
CARD_CSS = """
<style>
:root { --card-border: VAR_BORDER; --font-col: VAR_FONT; --muted-col: VAR_MUTED; }
.compact .card {
  background: rgba(255,255,255,.6);
  border: 2px solid var(--card-border);
  border-radius: 12px;
  padding: 10px;
  box-shadow: 0 2px 10px rgba(0,0,0,.08);
}
.compact h4 { margin:0 0 6px 0; font-weight:700; font-size:.92rem; color:var(--font-col); }
.compact .kpi {
  background: rgba(255,255,255,.6);
  border: 2px solid var(--card-border);
  border-radius: 10px; padding: 8px 10px;
  box-shadow: 0 2px 10px rgba(0,0,0,.06);
}
.compact .kpi .label { font-size:.72rem; color:var(--muted-col); margin-bottom:2px; }
.compact .kpi .value { font-weight:800; font-size:1rem; line-height:1.1; color:var(--font-col); }
.compact .kpi .muted { font-size:.68rem; color:var(--muted-col); }
</style>
"""

def use_compact_skin():
    css = (
        CARD_CSS
        .replace("VAR_BORDER", _THEME["card_border"])
        .replace("VAR_FONT", _THEME["font"])
        .replace("VAR_MUTED", _THEME["muted"])
    )
    st.markdown(css, unsafe_allow_html=True)

def kpi_row(items: List[dict], cols: int = 6):
    cols = st.columns(cols, vertical_alignment="center")
    for c, item in zip(cols, items):
        with c:
            st.markdown('<div class="kpi">', unsafe_allow_html=True)
            st.markdown(f'<div class="label">{item.get("label","")}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="value">{item.get("value","")}</div>', unsafe_allow_html=True)
            hint = item.get("hint")
            if hint:
                st.markdown(f'<div class="muted">{hint}</div>', unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

def card_start(title: str):
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown(f"<h4>{title}</h4>", unsafe_allow_html=True)

def card_end():
    st.markdown("</div>", unsafe_allow_html=True)

# ====== layout helper ======
def _apply_layout(fig, height: int):
    fig.update_layout(
        margin=dict(l=4, r=4, t=2, b=0),
        height=height,
        paper_bgcolor=_THEME["paper"],
        plot_bgcolor=_THEME["plot"],
        font=dict(color=_THEME["font"], size=11),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10))
    )
    return fig

# ====== CHARTS ======
def donut(counter: Dict[str, float], title: str, height: int = 150, key: Optional[str]=None):
    labels = list(counter.keys()) or ["N/A"]
    values = list(counter.values()) or [1]
    fig = px.pie(names=labels, values=values, hole=0.62)
    fig.update_traces(textinfo="percent", textposition="inside",
                      marker=dict(line=dict(color=_THEME["card_border"], width=1.4)))
    _apply_layout(fig, height)
    card_start(title); st.plotly_chart(fig, use_container_width=True, key=key); card_end()

def donut_tiny(counter: Dict[str, float], title: str, height: int = 110, key: Optional[str]=None):
    labels = list(counter.keys()) or ["N/A"]
    values = list(counter.values()) or [1]
    fig = px.pie(names=labels, values=values, hole=0.70)
    fig.update_traces(textinfo="none", marker=dict(line=dict(color=_THEME["card_border"], width=1)))
    _apply_layout(fig, height)
    card_start(title); st.plotly_chart(fig, use_container_width=True, key=key); card_end()

def gauge_semicircle(percent: float, title="Progress", height: int = 120, key: Optional[str]=None):
    value = max(0, min(100, percent))
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=value,
        number={'suffix': "%", 'font': {'size': 18, 'color': _THEME["font"]}},
        gauge={
            'shape': "angular",
            'axis': {'range':[0,100], 'visible': True, 'tickfont': {'size': 9}},
            'bar': {'color': _THEME["accent"]},
            'bgcolor': "rgba(0,0,0,0)",
            'borderwidth': 1.6, 'bordercolor': _THEME["card_border"]
        },
        domain={'x':[0,1], 'y':[0,0.55]}
    ))
    _apply_layout(fig, height)
    card_start(title); st.plotly_chart(fig, use_container_width=True, key=key); card_end()

def bullet(actual: float, target: float, title: str, height: int = 80, key: Optional[str]=None):
    # Bară tip bullet (actual vs target)
    actual = max(0, actual); target = max(actual, target)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[target], y=[" "], orientation='h',
                         marker=dict(color="rgba(148,163,184,.35)"), hoverinfo='skip'))
    fig.add_trace(go.Bar(x=[actual], y=[" "], orientation='h',
                         marker=dict(color=_THEME["accent"]), hovertemplate="Actual: %{x}<extra></extra>"))
    fig.update_layout(barmode="overlay")
    fig.update_xaxes(range=[0, target*1.05], showgrid=False)
    fig.update_yaxes(visible=False)
    _apply_layout(fig, height)
    card_start(title); st.plotly_chart(fig, use_container_width=True, key=key); card_end()

def bar(df: Optional[pd.DataFrame], x: str, y: str, title: str, height: int = 150, color: Optional[str]=None, stacked=False, key: Optional[str]=None):
    if df is None or df.empty:
        card_start(title); st.caption("Nu există date."); card_end(); return
    fig = px.bar(df, x=x, y=y, color=color)
    if stacked: fig.update_layout(barmode="stack")
    fig.update_traces(marker_line=dict(color=_THEME["card_border"], width=1.1))
    _apply_layout(fig, height)
    card_start(title); st.plotly_chart(fig, use_container_width=True, key=key); card_end()

def line(df: Optional[pd.DataFrame], x: str, y: str, title: str, height: int = 150, color: Optional[str]=None, key: Optional[str]=None):
    if df is None or df.empty:
        card_start(title); st.caption("Nu există date."); card_end(); return
    fig = px.line(df, x=x, y=y, color=color)
    fig.update_traces(line=dict(width=2.2))
    _apply_layout(fig, height)
    card_start(title); st.plotly_chart(fig, use_container_width=True, key=key); card_end()
