# containers/sections.py
from __future__ import annotations

import base64
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd
import streamlit as st

from utils.data_loader import data, PROJECTS_XLSX

APP_ROOT = Path(__file__).resolve().parents[1]
ATTACH_DIR = APP_ROOT / "attachments"
ATTACH_DIR.mkdir(parents=True, exist_ok=True)

# ----------------- Helpers -----------------
def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")

def _proj_row(df: pd.DataFrame, proj_id: str) -> Optional[pd.Series]:
    if df is None or df.empty:
        return None
    m = df["id"].astype(str) == str(proj_id)
    return df[m].iloc[0] if m.any() else None

def _parse_sections(row: pd.Series) -> Tuple[List[str], List[int]]:
    secs = [s.strip() for s in str(row.get("sections", "")).split(",") if s.strip()]
    raw_prog = str(row.get("sections_progress", "")).strip()
    progs = [p.strip() for p in raw_prog.split(",")] if raw_prog else []
    out: List[int] = []
    for p in progs:
        try:
            out.append(int(float(p)))
        except Exception:
            out.append(0)
    if len(out) < len(secs):
        out += [0] * (len(secs) - len(out))
    elif len(out) > len(secs):
        out = out[: len(secs)]
    return secs, out

def _save_files(files, proj_id: str, section: str) -> List[str]:
    paths: List[str] = []
    if not files:
        return paths
    t = ATTACH_DIR / str(proj_id) / section
    t.mkdir(parents=True, exist_ok=True)
    for f in files:
        name = f.name.replace("/", "_").replace("\\", "_")
        with open(t / name, "wb") as out:
            out.write(f.getbuffer())
        paths.append(str((t / name).relative_to(APP_ROOT)))
    return paths

def _render_attachment(path: Path):
    if not path.exists():
        return
    if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
        st.image(str(path), caption=path.name, use_container_width=True)
    elif path.suffix.lower() == ".pdf":
        try:
            with open(path, "rb") as fh:
                b64 = base64.b64encode(fh.read()).decode("utf-8")
            st.markdown(
                f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="320" style="border:0;border-radius:8px;"></iframe>',
                unsafe_allow_html=True,
            )
        except Exception:
            st.write(path.name)

def _append_note(row_idx: int, section: str, note: str, files_saved: List[str], user_name: str, visible_all: bool):
    try:
        df = pd.read_excel(PROJECTS_XLSX, sheet_name="Proiecte", engine="openpyxl")
    except Exception:
        st.error("Nu pot deschide fișierul Proiecte.")
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    files_str = ", ".join(files_saved) if files_saved else ""
    entry = f"[UPD][{now}][USER:{user_name}][SEC:{section}][ALL:{1 if visible_all else 0}] {note.strip()} | FILES: {files_str}"
    prev = str(df.at[row_idx, "notes"]) if "notes" in df.columns and pd.notna(df.at[row_idx, "notes"]) else ""
    df.at[row_idx, "notes"] = (prev + ("\n" if prev else "") + entry).strip()
    with pd.ExcelWriter(PROJECTS_XLSX, engine="openpyxl", mode="w") as xlw:
        df.to_excel(xlw, sheet_name="Proiecte", index=False)

def _update_progress(proj_id: str, section: str, new_prog: int, note: str, files_saved: List[str], user_name: str, visible_all: bool):
    """Actualizează progresul secției și progress_overall în data/proiecte.xlsx."""
    try:
        df = pd.read_excel(PROJECTS_XLSX, sheet_name="Proiecte", engine="openpyxl")
    except Exception:
        st.error("Nu pot deschide fișierul Proiecte.")
        return

    if df.empty or "id" not in df.columns:
        st.error("Nu găsesc proiectele în fișier.")
        return

    mask = df["id"].astype(str) == str(proj_id)
    if not mask.any():
        st.error("Proiectul selectat nu a fost găsit.")
        return

    i = df.index[mask][0]
    secs, prog = _parse_sections(df.loc[i])
    if section not in secs:
        st.error(f"Secția «{section}» nu există în acest proiect.")
        return
    idx = secs.index(section)
    prog[idx] = int(new_prog)

    df.at[i, "sections_progress"] = ", ".join(str(x) for x in prog)
    df.at[i, "progress_overall"] = float(round(sum(prog) / max(len(prog), 1), 1))

    # notă + atașamente
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    files_str = ", ".join(files_saved) if files_saved else ""
    entry = f"[UPD][{now}][USER:{user_name}][SEC:{section}][ALL:{1 if visible_all else 0}] {note.strip()} | FILES: {files_str}"
    prev_notes = str(df.at[i, "notes"]) if "notes" in df.columns and pd.notna(df.at[i, "notes"]) else ""
    df.at[i, "notes"] = (prev_notes + ("\n" if prev_notes else "") + entry).strip()

    with pd.ExcelWriter(PROJECTS_XLSX, engine="openpyxl", mode="w") as xlw:
        df.to_excel(xlw, sheet_name="Proiecte", index=False)

def _normalize_users_df(dfu: Optional[pd.DataFrame]) -> pd.DataFrame:
    """Asigură că există coloanele minime pentru utilizatori."""
    if dfu is None:
        return pd.DataFrame(columns=["name", "email", "section", "responsible", "role"])
    u = dfu.copy()
    for c in ["name", "email", "section", "responsible", "role"]:
        if c not in u.columns:
            u[c] = "" if c != "responsible" else 0
    u["name"] = u["name"].astype(str)
    u["email"] = u["email"].astype(str)
    u["section"] = u["section"].astype(str)
    # responsible -> int 0/1
    try:
        u["responsible"] = pd.to_numeric(u["responsible"], errors="coerce").fillna(0).astype(int)
    except Exception:
        u["responsible"] = 0
    return u[["name", "email", "section", "responsible", "role"]].copy()

def _section_defaults(section: str, df_users: Optional[pd.DataFrame]) -> Tuple[Optional[str], List[str]]:
    """
    Găsește un responsabil implicit (responsible=1) pentru secția dată
    și lista de utilizatori disponibili în secție (nume).
    Robustețe: dacă lipsesc coloanele, returnează (None, []).
    """
    u = _normalize_users_df(df_users)
    if u.empty:
        return None, []
    m = u["section"].str.contains(re.escape(section), case=False, na=False)
    pool = u[m].copy()
    resp_name = None
    if not pool.empty:
        main = pool[pool["responsible"] == 1]
        if not main.empty:
            resp_name = str(main.iloc[0]["name"])
    return resp_name, pool["name"].astype(str).tolist()

# ----------------- UI -----------------
def render(ctx=None, **kwargs):
    st.markdown(
        """
        <style>
          .sec-card{border:1px solid #e5e7eb;border-radius:12px;padding:12px;margin-bottom:10px;background:#fffef8;}
          .muted{color:#6b7280}
          .tag{display:inline-block;padding:2px 8px;border-radius:999px;background:#eef2ff;border:1px solid #c7d2fe;margin-right:6px;}
          .adj{display:inline-block;padding:2px 8px;border-radius:999px;background:#fff7ed;border:1px solid #fed7aa;margin-left:8px;}
          .pill{display:inline-block;padding:2px 8px;border:1px solid #e5e7eb;border-radius:999px;margin-right:6px;background:#fff;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("## 🏭 Secțiuni — Board operator")

    dfp = data.projects.copy()
    dfu = _normalize_users_df(data.users.copy() if hasattr(data, "users") else None)

    if dfp is None or dfp.empty:
        st.warning("Nu există proiecte încărcate.")
        return

    # ---- Filtre sus
    c1, c2, c3, c4 = st.columns([1.5, 1.2, 1.2, 1.3])
    with c1:
        options = dfp["id"].astype(str) + " • " + dfp["name"].astype(str)
        mapping = dict(zip(options, dfp["id"].astype(str)))
        sel_opt = st.selectbox("Proiect", options.tolist(), index=0)
        proj_id = mapping[sel_opt]
    row = _proj_row(dfp, proj_id)
    if row is None:
        st.error("Proiectul selectat nu a fost găsit.")
        return
    secs, progs = _parse_sections(row)

    with c2:
        sec_filter = st.selectbox("Filtru secție", ["Toate"] + secs, index=0)
    with c3:
        resp_global = st.text_input("Filtru responsabil (nume conține)", "")
    with c4:
        search = st.text_input("Căutare text (proiect/secție/notițe)", "")

    # determinăm ordinea: ultima secție deschisă prima
    last_key = st.session_state.get("last_section_key")
    order = secs.copy()
    if isinstance(last_key, str) and last_key.startswith(str(proj_id) + ":"):
        last_sec = last_key.split(":", 1)[1]
        if last_sec in order:
            order.remove(last_sec)
            order = [last_sec] + order

    def _sec_visible(sec_name: str) -> bool:
        if sec_filter != "Toate" and sec_name != sec_filter:
            return False
        if search.strip():
            q = search.strip().lower()
            text = f"{row.get('name','')} {row.get('company','')} {sec_name} {row.get('notes','')}".lower()
            if q not in text:
                return False
        if resp_global.strip():
            q2 = resp_global.strip().lower()
            rname, pool = _section_defaults(sec_name, dfu)
            s = (rname or "") + " " + ", ".join(pool)
            if q2 not in s.lower():
                return False
        return True

    # ---- Afișare carduri secții
    expanded_done = False
    for idx, sec in enumerate(order):
        if not _sec_visible(sec):
            continue
        cur_prog = progs[secs.index(sec)] if sec in secs else 0

        sec_key = f"{proj_id}:{sec}"
        expanded = (not expanded_done and (st.session_state.get("last_section_key") == sec_key)) or \
                   (not expanded_done and sec_filter != "Toate" and sec == sec_filter)
        if not expanded_done and st.session_state.get("last_section_key") is None and idx == 0:
            expanded = True
        if expanded:
            expanded_done = True

        with st.container():
            if expanded:
                st.markdown(f"### {sec} <span class='tag'>progres: {cur_prog}%</span>", unsafe_allow_html=True)
                a, b, c = st.columns([1, 1, 1])

                # --- COL A: progres + utilizatori
                with a:
                    new_prog = st.slider(f"Progres {sec}", 0, 100, int(cur_prog), key=f"prog_{sec_key}")
                    adjusted = new_prog != int(cur_prog)
                    if adjusted:
                        st.markdown("<span class='adj'>ajustare manuală</span>", unsafe_allow_html=True)

                    rname, pool = _section_defaults(sec, dfu)
                    st.caption("Responsabil secție (sugerat):")
                    st.write(rname or "_neatribuit_")
                    part_sel = st.multiselect("Coparticipanți (din secție)", options=pool, default=[], key=f"parts_{sec_key}")

                # --- COL B: adnotări + upload + vizibilitate
                with b:
                    note = st.text_area("Adnotare", height=140, key=f"note_{sec_key}", placeholder="Note interne pentru această secție…")
                    files = st.file_uploader("Documente (png/jpg/webp/pdf)", type=["png","jpg","jpeg","webp","pdf"], accept_multiple_files=True, key=f"files_{sec_key}")
                    visible_all = st.checkbox("Vizibil pentru toate secțiile", value=False, key=f"vis_{sec_key}")
                    if files:
                        st.caption("Previzualizări:")
                        for f in files[:2]:
                            name = f.name.lower()
                            if any(name.endswith(ext) for ext in (".png",".jpg",".jpeg",".webp")):
                                st.image(f, use_container_width=True)
                            elif name.endswith(".pdf"):
                                try:
                                    b64 = base64.b64encode(f.getvalue()).decode("utf-8")
                                    st.markdown(
                                        f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="180" style="border:0;"></iframe>',
                                        unsafe_allow_html=True,
                                    )
                                except Exception:
                                    pass

                # --- COL C: atașamente + istoric
                with c:
                    st.caption("Atașamente salvate")
                    att_dir = ATTACH_DIR / str(proj_id) / sec
                    found = False
                    if att_dir.exists():
                        for sub in sorted(att_dir.glob("*")):
                            if sub.suffix.lower() in (".png",".jpg",".jpeg",".webp",".pdf"):
                                found = True
                                _render_attachment(sub)
                    if not found:
                        st.caption("_Niciun fișier salvat încă._")

                    st.caption("Istoric (ultimele actualizări)")
                    for ln in _history_for_section(str(row.get("notes", "")), sec, limit=5):
                        st.write("• " + ln)

                c1, c2, _ = st.columns([1, 1, 2])
                with c1:
                    if st.button("💾 Salvează", key=f"save_{sec_key}"):
                        saved_paths = _save_files(files, str(proj_id), sec)
                        user_name = st.session_state.get("auth_name") or st.session_state.get("current_user_name") or "User"
                        assign_info = ""
                        if rname or part_sel:
                            assign_info = f" | ASSIGN: resp={rname or '-'}; parts={', '.join(part_sel) if part_sel else '-'}"
                        _update_progress(str(proj_id), sec, int(new_prog), (note or "") + assign_info, saved_paths, user_name, bool(visible_all))
                        data.refresh()
                        st.session_state["last_section_key"] = sec_key
                        st.success("Modificările au fost salvate.")
                        st.experimental_rerun()
                with c2:
                    if st.button("Pliază secția", key=f"fold_{sec_key}"):
                        st.session_state["last_section_key"] = None
                        st.experimental_rerun()

                st.divider()
            else:
                with st.container():
                    st.markdown(
                        f"<div class='sec-card'><b>{sec}</b> · "
                        f"<span class='pill'>progres: {cur_prog}%</span> "
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    colx, coly = st.columns([1, 5])
                    with colx:
                        st.progress(int(cur_prog) / 100.0)
                    with coly:
                        rname, pool = _section_defaults(sec, dfu)
                        st.caption(f"Responsabil sugerat: {rname or '–'}  ·  Operatori: {', '.join(pool[:4]) + ('…' if len(pool) > 4 else '')}")
                        if st.button("Editează", key=f"expand_{sec_key}"):
                            st.session_state["last_section_key"] = sec_key
                            st.experimental_rerun()

def _history_for_section(notes: str, section: str, limit: int = 6) -> List[str]:
    if not notes:
        return []
    lines = [ln.strip() for ln in str(notes).splitlines() if "[UPD]" in ln]
    out = [ln for ln in lines if f"[SEC:{section}]" in ln]
    return out[-limit:]
