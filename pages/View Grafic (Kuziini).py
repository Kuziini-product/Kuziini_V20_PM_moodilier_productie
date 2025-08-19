# Title: Kuziini – Board Compact (2 coloane, stivuit)
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import numpy as np
import sys
from pathlib import Path
import plotly.express as px  # doar pentru histogramă dacă vrei s-o adaugi

# ====== setup & stil ======
st.set_page_config(layout="wide")
st.markdown("""
<style>
.block-container { padding-top:.5rem; padding-bottom:.5rem; max-width: 1500px; }
footer {visibility:hidden;}
/* 2 coloane cu spațiere mică */
.section { display:grid; grid-template-columns: repeat(2, 1fr); gap:8px; }
/* mini grile în interiorul fiecărei secțiuni */
.grid3 { display:grid; grid-template-columns: repeat(3, minmax(160px,1fr)); gap:8px; }
.grid2 { display:grid; grid-template-columns: repeat(2, minmax(180px,1fr)); gap:8px; }
.grid4 { display:grid; grid-template-columns: repeat(4, minmax(140px,1fr)); gap:8px; }
/* subtitluri compacte */
h2, h3 { margin: .2rem 0 .5rem 0; }
</style>
""", unsafe_allow_html=True)

# ====== import components/charts ======
def _ensure_components_on_path():
    here = Path(__file__).resolve()
    for i in range(1, 5):
        root = here.parents[i]
        comp = root / "components"
        if comp.exists() and (comp / "charts.py").exists():
            if str(root) not in sys.path:
                sys.path.insert(0, str(root))
            return
    local = here.parent.parent / "components"
    if local.exists() and (local / "charts.py").exists():
        if str(here.parent.parent) not in sys.path:
            sys.path.insert(0, str(here.parent.parent))
_ensure_components_on_path()

from components.charts import (
    set_theme, use_compact_skin, kpi_row,
    donut_tiny, gauge_semicircle, bullet, bar, line, card_start, card_end
)

# Tema – dacă vrei, poți lega accentul de o culoare de brand
set_theme(accent="#2563eb", font="#111827", card_border="#94a3b8")
use_compact_skin()

st.title("📊 Analiza-AI Organizatie")

# ====== încărcare date (din app sau CSV) ======
projects_df = tasks_df = schedule_df = teams_df = None
loaded = False
for mod, fn in [("utils.data","load_dataframes"), ("services.data","load_dataframes"), ("data_loader","load_dataframes")]:
    try:
        m = __import__(mod, fromlist=[fn]); loader = getattr(m, fn)
        projects_df, tasks_df, schedule_df, teams_df = loader()
        loaded = True; break
    except Exception: pass

if not loaded:
    try:
        projects_df = pd.read_csv("data/projects.csv")
        tasks_df    = pd.read_csv("data/tasks.csv")
        schedule_df = pd.read_csv("data/schedule.csv")
        teams_df    = pd.read_csv("data/teams.csv")
        loaded = True
    except Exception:
        pass

# fallback demo dacă nu există date
def _demo_projects():
    owners = ["Madalin", "Stefan", "Cristi", "Dana"]
    statuses = ["Planificare", "Execuție", "Finalizare", "On Hold"]
    rows = []
    for i in range(1, 13):
        rows.append({
            "project_id": f"P{i:03d}", "name": f"Proiect {i}",
            "owner": np.random.choice(owners),
            "status": np.random.choice(statuses, p=[0.25,0.45,0.2,0.1]),
            "budget": np.random.randint(3000,20000),
            "deadline": (datetime.today()+timedelta(days=np.random.randint(5,90))).date(),
        })
    return pd.DataFrame(rows)

def _demo_tasks(projects_df):
    statuses = ["To Do", "In Progress", "Review", "Done"]
    rows = []
    for _, p in projects_df.iterrows():
        for i in range(np.random.randint(4, 10)):
            prog = np.random.randint(0,100); plan = max(prog, np.random.randint(40,120))
            rows.append({
                "task_id": f"T{p.project_id}_{i+1}", "project_id": p.project_id,
                "title": f"Task {i+1} / {p['name']}",
                "status": np.random.choice(statuses, p=[0.35,0.35,0.1,0.2]),
                "progress": prog, "planned_progress": plan,
                "created_at": (datetime.today()-timedelta(days=np.random.randint(0,40))).date(),
                "assignee": p.owner,
            })
    return pd.DataFrame(rows)

if projects_df is None or tasks_df is None:
    projects_df = _demo_projects(); tasks_df = _demo_tasks(projects_df)
    schedule_df = pd.DataFrame();  teams_df = pd.DataFrame()

# ====== agregări ======
total_projects = len(projects_df)
in_exec  = int(projects_df["status"].eq("Execuție").sum()) if "status" in projects_df else 0
finished = int(projects_df["status"].eq("Finalizare").sum()) if "status" in projects_df else 0
on_hold  = int(projects_df["status"].eq("On Hold").sum()) if "status" in projects_df else 0

total_tasks = len(tasks_df)
tasks_done   = int(tasks_df["status"].eq("Done").sum()) if "status" in tasks_df else 0
tasks_inprog = int(tasks_df["status"].eq("In Progress").sum()) if "status" in tasks_df else 0
tasks_review = int(tasks_df["status"].eq("Review").sum()) if "status" in tasks_df else 0

actual  = float(tasks_df["progress"].sum()) if "progress" in tasks_df else 0.0
planned = float(tasks_df["planned_progress"].sum()) if "planned_progress" in tasks_df else max(actual, 100.0)
pct = 0 if planned == 0 else round(100*actual/planned, 1)

# KPI pe un rând – 6 casete mici
kpi_row([
    {"label":"Proiecte", "value": f"{total_projects}"},
    {"label":"În execuție", "value": f"{in_exec}"},
    {"label":"Finalizate", "value": f"{finished}"},
    {"label":"On Hold", "value": f"{on_hold}"},
    {"label":"Task-uri", "value": f"{total_tasks}", "hint": f"Done {tasks_done}"},
    {"label":"Progres global", "value": f"{pct}%"},
], cols=6)

st.divider()

# ====== layout pe 2 coloane ======
col_left, col_right = st.columns(2, gap="small")

# ==== STÂNGA: proiecte (mai multe cadrane pe verticală) ====
with col_left:
    st.subheader("Proiecte")
    st.markdown('<div class="grid4 compact">', unsafe_allow_html=True)
    # 4 cadrane ceas „micro”
    done_pct_global = 0 if total_projects==0 else round(100*finished/total_projects, 1)
    exec_pct        = 0 if total_projects==0 else round(100*in_exec/total_projects, 1)
    hold_pct        = 0 if total_projects==0 else round(100*on_hold/total_projects, 1)
    # pentru întârziere: dacă ai deadline, îl poți evalua aici (simplificat zero):
    late_pct        = 0.0
    gauge_semicircle(done_pct_global, "Finalizate %", height=110, key="g_proj_done")
    gauge_semicircle(exec_pct,        "În execuție %", height=110, key="g_proj_exec")
    gauge_semicircle(late_pct,        "Întârziere %", height=110, key="g_proj_late")
    gauge_semicircle(hold_pct,        "On Hold %",    height=110, key="g_proj_hold")
    st.markdown('</div>', unsafe_allow_html=True)

    # distribuții compacte
    st.markdown('<div class="grid2 compact" style="margin-top:8px;">', unsafe_allow_html=True)
    if "owner" in projects_df:
        df_by_owner = projects_df.groupby("owner").size().reset_index(name="count")
    else:
        df_by_owner = pd.DataFrame(columns=["owner","count"])
    bar(df_by_owner, "owner", "count", "Proiecte / Responsabil", height=140, key="bar_proj_owner")

    if "status" in projects_df:
        df_by_status = projects_df["status"].value_counts().reset_index()
        df_by_status.columns = ["status","count"]
    else:
        df_by_status = pd.DataFrame(columns=["status","count"])
    bar(df_by_status, "status", "count", "Proiecte / Status", height=140, key="bar_proj_status")
    st.markdown('</div>', unsafe_allow_html=True)

    # bullet global
    bullet(actual, planned if planned>0 else max(100, actual), "Actual vs Plan (Global)", height=80, key="b_global")

# ==== DREAPTA: task-uri (mai multe cadrane pe verticală) ====
with col_right:
    st.subheader("Task-uri")
    st.markdown('<div class="grid4 compact">', unsafe_allow_html=True)
    # 4 cadrane ceas „micro” pentru task-uri
    tot_pct     = 100
    done_pct    = 0 if total_tasks==0 else round(100*tasks_done/total_tasks, 1)
    inprog_pct  = 0 if total_tasks==0 else round(100*tasks_inprog/total_tasks, 1)
    review_pct  = 0 if total_tasks==0 else round(100*tasks_review/total_tasks, 1)
    gauge_semicircle(tot_pct,    "Total",        height=110, key="g_tasks_total")
    gauge_semicircle(done_pct,   "Done %",       height=110, key="g_tasks_done")
    gauge_semicircle(inprog_pct, "In Progress %",height=110, key="g_tasks_inprog")
    gauge_semicircle(review_pct, "Review %",     height=110, key="g_tasks_review")
    st.markdown('</div>', unsafe_allow_html=True)

    # evoluții compacte
    st.markdown('<div class="grid2 compact" style="margin-top:8px;">', unsafe_allow_html=True)
    if "created_at" in tasks_df:
        t = tasks_df.copy(); t["date"] = pd.to_datetime(t["created_at"]).dt.date
        timeline = t.groupby("date").size().reset_index(name="count")
    else:
        timeline = pd.DataFrame(columns=["date","count"])
    line(timeline, "date", "count", "Task-uri / zi", height=140, key="line_tasks_day")

    if {"assignee","status"}.issubset(tasks_df.columns):
        stacked = tasks_df.groupby(["assignee","status"]).size().reset_index(name="count")
    else:
        stacked = pd.DataFrame(columns=["assignee","status","count"])
    bar(stacked, "assignee", "count", "Task-uri / Responsabil (stacked)", height=140, color="status", stacked=True, key="bar_tasks_stack")
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()
st.caption("Vedere compactă: două coloane, carduri mici, mai multe cadrane pe rând. Vizualul standard rămâne neschimbat.")
