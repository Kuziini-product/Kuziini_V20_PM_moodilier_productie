# containers/users.py
from __future__ import annotations

import base64
import re
from io import BytesIO
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

from utils.data_loader import data

# --- Căi & fișiere ---
APP_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = APP_ROOT / "data"
AVATAR_DIR = APP_ROOT / "assets" / "avatars"
AVATAR_DIR.mkdir(parents=True, exist_ok=True)

# Fişierul principal pentru utilizatori (personal)
try:
    from utils.data_loader import PERSONAL_XLSX  # preferăm constanta existentă
except Exception:  # fallback
    PERSONAL_XLSX = DATA_DIR / "personal.xlsx"

# Fişierul pentru roluri & permisiuni
ROLES_XLSX = DATA_DIR / "roles_permissions.xlsx"

USERS_COLS = ["id", "name", "email", "section", "responsible", "role"]
DEFAULT_ROLES = ["Vizitator", "Operator", "Manager", "Admin"]
PERM_KEYS = [
    "view_dashboard",
    "view_overview",
    "view_sections",
    "view_user_profile",
    "create_order",
    "project_settings",
    "users_admin",
    "data_check",
]

# ----------------- HELPERS -----------------
def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(s).lower()).strip("_")

def _avatar_path(email: str, name: str) -> Path:
    if email:
        return AVATAR_DIR / f"{_slug(email)}.png"
    return AVATAR_DIR / f"{_slug(name)}.png"

def _ensure_users_schema(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in USERS_COLS:
        if c not in df.columns:
            df[c] = None
    df["id"] = pd.to_numeric(df["id"], errors="coerce").astype("Int64")
    df["name"] = df["name"].astype(str).str.strip()
    df["email"] = df["email"].astype(str).str.strip()
    df["section"] = df["section"].astype(str).str.strip()
    df["responsible"] = pd.to_numeric(df["responsible"], errors="coerce").fillna(0).astype(int)
    df["role"] = df["role"].astype(str).str.strip()
    return df[USERS_COLS].copy()

def _read_users() -> pd.DataFrame:
    try:
        df = pd.read_excel(PERSONAL_XLSX, sheet_name="Personal", engine="openpyxl")
    except Exception:
        df = pd.DataFrame(columns=USERS_COLS)
    return _ensure_users_schema(df)

def _write_users(df: pd.DataFrame) -> None:
    df = _ensure_users_schema(df)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(PERSONAL_XLSX, engine="openpyxl", mode="w") as xlw:
        df.to_excel(xlw, sheet_name="Personal", index=False)

def _next_user_id(df: pd.DataFrame) -> int:
    if df.empty or df["id"].isna().all():
        return 1
    return int(pd.to_numeric(df["id"], errors="coerce").fillna(0).max()) + 1

def _preview_upload(file):
    if not file:
        return
    name = file.name.lower()
    if any(name.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".webp")):
        st.image(file, caption=file.name, use_container_width=True)
    elif name.endswith(".pdf"):
        b64 = base64.b64encode(file.getvalue()).decode("utf-8")
        st.markdown(
            f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="320" style="border:1px solid #bbb;border-radius:8px;"></iframe>',
            unsafe_allow_html=True,
        )

def _download_excel(df: pd.DataFrame, filename: str, sheet: str = "Sheet1"):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xlw:
        df.to_excel(xlw, index=False, sheet_name=sheet)
    st.download_button(
        "⬇️ Descarcă",
        data=buf.getvalue(),
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

def _load_roles() -> pd.DataFrame:
    try:
        df = pd.read_excel(ROLES_XLSX, sheet_name="Permissions", engine="openpyxl")
    except Exception:
        rows = []
        for r in DEFAULT_ROLES:
            row = {"role": r}
            for k in PERM_KEYS:
                row[k] = True if r in ("Manager", "Admin") else k in [
                    "view_dashboard",
                    "view_overview",
                    "view_sections",
                    "view_user_profile",
                ]
            rows.append(row)
        df = pd.DataFrame(rows)
    if "role" not in df.columns:
        df.insert(0, "role", DEFAULT_ROLES)
    for k in PERM_KEYS:
        if k not in df.columns:
            df[k] = False
    return df[["role"] + PERM_KEYS].copy()

def _save_roles(df: pd.DataFrame) -> None:
    df = df.copy()
    for k in PERM_KEYS:
        df[k] = df[k].astype(bool)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(ROLES_XLSX, engine="openpyxl", mode="w") as xlw:
        df.to_excel(xlw, sheet_name="Permissions", index=False)

# ----------------- UI -----------------
def render(ctx=None, **kwargs):
    st.markdown(
        """
        <style>
          .small-card{border:1px solid #e5e7eb;border-radius:10px;padding:8px;background:#fffef8;}
          .muted{color:#6b7280}
          .chip{display:inline-block;padding:3px 10px;border:1px solid #e5e7eb;border-radius:999px;margin-right:6px;margin-bottom:6px;background:#fff;}
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("## 👥 Utilizatori — administrare")

    df = _read_users()

    tab_list, tab_add, tab_io, tab_roles = st.tabs(
        ["Lista & editare", "Adaugă utilizator", "Import / Export", "Roluri & permisiuni"]
    )

    # ---------- TAB: LISTA & EDITARE ----------
    with tab_list:
        left, right = st.columns([2, 3])

        with left:
            st.markdown("### 📋 Lista utilizatori")
            q = st.text_input("Căutare (nume, email, secție, rol)", "")
            filt = df.copy()
            if q.strip():
                qre = re.escape(q.strip())
                mask = (
                    filt["name"].str.contains(qre, case=False, na=False)
                    | filt["email"].str.contains(qre, case=False, na=False)
                    | filt["section"].str.contains(qre, case=False, na=False)
                    | filt["role"].str.contains(qre, case=False, na=False)
                )
                filt = filt[mask]

            st.dataframe(
                filt[USERS_COLS],
                use_container_width=True,
                height=560,  # tabel mai înalt
                column_config={
                    "id": st.column_config.NumberColumn("ID"),
                    "name": st.column_config.TextColumn("Nume"),
                    "email": st.column_config.TextColumn("Email"),
                    "section": st.column_config.TextColumn("Secție"),
                    "responsible": st.column_config.CheckboxColumn("Responsabil"),
                    "role": st.column_config.TextColumn("Rol"),
                },
                hide_index=True,
            )

            ids = df["id"].dropna().astype(int).astype(str).tolist()
            sel: Optional[str] = None
            if ids:
                sel = st.selectbox("Selectează utilizator pentru editare", options=ids, index=0)
            else:
                st.info("Nu există utilizatori încă. Adaugă din tabul următor.")

        with right:
            st.markdown("### ✏️ Editare utilizator")
            if not df.empty and ids and sel is not None:
                u = df[df["id"].astype(str) == str(sel)].iloc[0]
                colA, colB = st.columns([1, 2])
                with colA:
                    avp = _avatar_path(str(u["email"]), str(u["name"]))
                    if avp.exists():
                        st.image(str(avp), caption="Avatar", use_container_width=True)
                    else:
                        st.caption("_fără avatar_")
                    up = st.file_uploader(
                        "Încarcă avatar", type=["png", "jpg", "jpeg", "webp"], key=f"up_{sel}"
                    )
                    if up is not None:
                        with open(avp, "wb") as f:
                            f.write(up.getvalue())
                        st.success("Avatar salvat.")
                with colB:
                    name = st.text_input("Nume complet", value=str(u["name"]))
                    email = st.text_input("Email", value=str(u["email"]))
                    section = st.text_input(
                        "Secție (sau multiple, separate prin ,)", value=str(u["section"])
                    )
                    role = st.selectbox(
                        "Rol",
                        DEFAULT_ROLES,
                        index=(DEFAULT_ROLES.index(str(u["role"])) if str(u["role"]) in DEFAULT_ROLES else 0),
                    )
                    responsible = st.checkbox(
                        "Utilizator principal (responsabil secție)", value=bool(int(u["responsible"] or 0))
                    )
                    save = st.button("💾 Salvează modificările")
                    del_user = st.button("🗑️ Șterge utilizatorul")

                if save:
                    if not name.strip() or not email.strip():
                        st.error("Nume și email sunt obligatorii.")
                    else:
                        idx = df.index[df["id"].astype(str) == str(sel)][0]
                        df.at[idx, "name"] = name.strip()
                        df.at[idx, "email"] = email.strip()
                        df.at[idx, "section"] = section.strip()
                        df.at[idx, "role"] = role
                        df.at[idx, "responsible"] = 1 if responsible else 0
                        _write_users(df)
                        data.refresh()
                        st.success("Utilizator actualizat.")

                if del_user:
                    df2 = df[df["id"].astype(str) != str(sel)].copy()
                    _write_users(df2)
                    data.refresh()
                    st.success("Utilizator șters.")
                    st.experimental_rerun()
            else:
                st.caption("Selectează un utilizator din lista din stânga pentru editare.")

    # ---------- TAB: ADAUGĂ ----------
    with tab_add:
        st.markdown("### ➕ Adaugă utilizator nou")
        c1, c2 = st.columns(2)
        with c1:
            name_new = st.text_input("Nume complet", key="add_name")
            email_new = st.text_input("Email", key="add_email")
            section_new = st.text_input("Secție (sau multiple, separate prin ,)", key="add_section")
        with c2:
            role_new = st.selectbox("Rol", DEFAULT_ROLES, index=1, key="add_role")
            responsible_new = st.checkbox(
                "Utilizator principal (responsabil secție)", value=False, key="add_resp"
            )
            avatar_new = st.file_uploader(
                "Avatar (opțional)", type=["png", "jpg", "jpeg", "webp"], key="add_avatar"
            )

        if st.button("✅ Creează utilizator", key="add_btn"):
            if not name_new.strip() or not email_new.strip():
                st.error("Nume și email sunt obligatorii.")
            else:
                df = _read_users()
                if email_new.strip().lower() in df["email"].astype(str).str.lower().tolist():
                    st.error("Există deja un utilizator cu acest email.")
                else:
                    new_id = _next_user_id(df)
                    row = {
                        "id": new_id,
                        "name": name_new.strip(),
                        "email": email_new.strip(),
                        "section": section_new.strip(),
                        "responsible": 1 if responsible_new else 0,
                        "role": role_new,
                    }
                    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
                    _write_users(df)
                    if avatar_new is not None:
                        with open(_avatar_path(email_new, name_new), "wb") as f:
                            f.write(avatar_new.getvalue())
                    data.refresh()
                    st.success(f"Utilizatorul #{new_id} a fost creat.")

    # ---------- TAB: IMPORT / EXPORT ----------
    with tab_io:
        st.markdown("### 🔁 Import / Export utilizatori")
        colL, colR = st.columns([1.1, 1])
        with colL:
            st.markdown("**Export**")
            st.caption("• *Șablon (cap de tabelă)* sau *lista curentă*.")
            tmpl = pd.DataFrame(columns=USERS_COLS)
            st.write("Șablon cap de tabelă")
            _download_excel(tmpl, "users_template.xlsx", sheet="Personal")
            st.write("Utilizatori existenți")
            _download_excel(_read_users(), "users_current.xlsx", sheet="Personal")

        with colR:
            st.markdown("**Import**")
            st.caption(
                "• Fișier Excel cu foaia **Personal** și coloanele: " + ", ".join(USERS_COLS)
            )
            up_file = st.file_uploader(
                "Încarcă fișier .xlsx", type=["xlsx"], key="up_users_xlsx"
            )

            mode = st.radio(
                "Mod import",
                ["Adaugă la lista actuală", "Înlocuiește lista (șterge tot)"],
                index=0,
                key="imp_mode",
            )
            confirm = st.checkbox("Confirm acțiunea selectată", key="imp_confirm")
            btn_check = st.button("🔍 Verificare fișier", key="imp_check")
            btn_import = st.button("📥 Importă", key="imp_do")

            import_df: Optional[pd.DataFrame] = None
            if up_file and (btn_check or btn_import):
                try:
                    import_df = pd.read_excel(
                        up_file, sheet_name="Personal", engine="openpyxl"
                    )
                except Exception as e:
                    st.error(f"Nu pot citi fișierul: {e}")
                    import_df = None

                if import_df is not None:
                    missing = [c for c in USERS_COLS if c not in import_df.columns]
                    if missing:
                        st.error("Lipsesc coloanele: " + ", ".join(missing))
                        import_df = None
                    else:
                        import_df = _ensure_users_schema(import_df)
                        st.success("Fișier valid.")
                        st.dataframe(import_df.head(20), use_container_width=True)

            if btn_import:
                if not confirm:
                    st.error("Bifează confirmarea înainte de import.")
                elif import_df is None:
                    st.error("Încarcă și verifică fișierul înainte de import.")
                else:
                    cur = _read_users()
                    if mode.startswith("Înlocuiește"):
                        final_df = import_df.copy()
                    else:
                        merged = pd.concat([cur, import_df], ignore_index=True)
                        no_id_mask = merged["id"].isna() | (merged["id"] == 0)
                        if no_id_mask.any():
                            start_id = _next_user_id(cur)
                            new_ids = list(
                                range(start_id, start_id + int(no_id_mask.sum()))
                            )
                            merged.loc[no_id_mask, "id"] = new_ids
                        merged["__key__"] = (
                            merged["email"].astype(str).fillna("").str.lower()
                        )
                        merged = merged.drop_duplicates(
                            subset="__key__", keep="last"
                        ).drop(columns="__key__")
                        final_df = merged
                    _write_users(final_df)
                    data.refresh()
                    st.success(f"Import finalizat. Total utilizatori: {final_df.shape[0]}")

    # ---------- TAB: ROLURI & PERMISIUNI ----------
    with tab_roles:
        st.markdown("### 🧑‍💼 Rol pe utilizator")
        st.caption(
            "Caută utilizatorul, modifică rapid rolul și salvează. Mai jos poți configura permisiunile pe rol."
        )

        users_df = _read_users()
        uq = st.text_input("Caută utilizator (nume/email/secție)", "", key="role_search")
        uview = users_df.copy()
        if uq.strip():
            uqre = re.escape(uq.strip())
            umask = (
                uview["name"].str.contains(uqre, case=False, na=False)
                | uview["email"].str.contains(uqre, case=False, na=False)
                | uview["section"].str.contains(uqre, case=False, na=False)
                | uview["role"].str.contains(uqre, case=False, na=False)
            )
            uview = uview[umask]

        role_column = st.column_config.SelectboxColumn(
            "Rol", options=DEFAULT_ROLES, help="Rolul utilizatorului"
        )
        edited_users = st.data_editor(
            uview[USERS_COLS],
            use_container_width=True,
            height=360,
            hide_index=True,
            column_config={
                "id": st.column_config.NumberColumn("ID"),
                "name": st.column_config.TextColumn("Nume"),
                "email": st.column_config.TextColumn("Email"),
                "section": st.column_config.TextColumn("Secție"),
                "responsible": st.column_config.CheckboxColumn("Responsabil"),
                "role": role_column,
            },
            disabled=["id", "name", "email", "section", "responsible"],  # edităm doar rolul
        )

        if st.button("💾 Salvează rolurile selectate", key="roles_save_users"):
            base = users_df.set_index("id")
            for _, r in edited_users.iterrows():
                uid = int(r["id"]) if pd.notna(r["id"]) else None
                if uid is None or uid not in base.index:
                    continue
                base.at[uid, "role"] = str(r["role"]) if pd.notna(r["role"]) else base.at[uid, "role"]
            _write_users(base.reset_index())
            data.refresh()
            st.success("Roluri actualizate pentru utilizatorii selectați.")

        st.markdown("---")
        st.markdown("### 🔐 Permisiuni pe rol (data/roles_permissions.xlsx)")
        roles_df = _load_roles()
        st.caption(
            "Bifează permisiunile per rol. Aceste setări NU restricționează încă celelalte pagini — le folosim ca sursă de adevăr."
        )
        edited_roles = st.data_editor(
            roles_df,
            use_container_width=True,
            num_rows="dynamic",
            column_config={k: st.column_config.CheckboxColumn(k, help=k) for k in PERM_KEYS},
            hide_index=True,
        )
        if st.button("💾 Salvează permisiunile pe rol", key="roles_save_matrix"):
            edited_roles = edited_roles.copy()
            edited_roles["role"] = edited_roles["role"].fillna("").replace("", "Custom")
            _save_roles(edited_roles)
            st.success("Permisiuni salvate.")
