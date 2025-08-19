# containers/new_order.py
from __future__ import annotations

import base64
from datetime import date, timedelta
from math import ceil
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import pandas as pd
import streamlit as st
from urllib.parse import quote_plus

from utils.data_loader import (
    data,
    SECTIONS,
    PROJECTS_XLSX,
    PROJECT_COLS_ORDER,
)

# --- opțional pentru Gantt (fallback dacă nu e instalat) ---
try:
    import altair as alt
except Exception:  # pragma: no cover
    alt = None

APP_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = APP_ROOT / "data"
ATTACH_DIR = APP_ROOT / "attachments"
OFFERS_XLSX = DATA_DIR / "oferte.xlsx"
ATTACH_DIR.mkdir(exist_ok=True)

# ---------- Capacități/Norme ----------
SEC_CAPACITY_HPD = {  # ore pe zi/ secție (simplificat)
    "Ofertare": 12, "Proiectare & Design": 16, "Tehnologică": 12, "Achiziții": 12,
    "CNC": 24, "Debitare": 16, "Furnir": 16, "Pregătire vopsitorie": 16,
    "Vopsitorie": 16, "Asamblare": 24, "CTC": 16, "Ambalare": 16,
    "Transport (Livrare)": 8, "Montaj": 16,
}

# Rate orare pe m² de front
PAINT_PREP_H_PER_M2 = 1.5
PAINT_COAT_H_PER_M2 = 2.0
VENEER_H_PER_M2 = 1.6

# Ambalare
PACK_BASE_H = 0.5
PACK_H_PER_M3 = 0.8
VOLUME_REDUCTION_DEZASAMBLAT = 0.65
PACK_FACTOR_ASAMBLAT = 1.5
PACK_FACTOR_DEZASAMBLAT = 1.0

# Durate fallback (zile) dacă nu există configurare
NORM_DAYS_FALLBACK = {
    "Ofertare": 1, "Proiectare & Design": 3, "Tehnologică": 2, "Achiziții": 2,
    "CNC": 2, "Debitare": 1, "Furnir": 2, "Pregătire vopsitorie": 2, "Vopsitorie": 3,
    "Asamblare": 3, "CTC": 1, "Ambalare": 1, "Transport (Livrare)": 1, "Montaj": 2,
}

# Recomandări default tranșe
RECO_SPLITS = {1: [100], 2: [70, 30], 3: [50, 45, 5], 4: [50, 25, 20, 5]}

# Baza ore per unitate (simplificată) pentru dulapuri
BASE_HOURS_PER_UNIT = {
    "CNC": 2.5,
    "Asamblare": 1.8,
    "CTC": 0.4,
    "Ambalare": 0.4,  # ambalare suplimentar față de PACK_H_PER_M3
}

# ---------- Helpers generale ----------
def _next_project_id(dfp: pd.DataFrame) -> str:
    year = date.today().year
    nums = []
    for v in dfp.get("id", []):
        s = str(v)
        if s.startswith(f"P-{year}-"):
            try:
                nums.append(int(s.split("-")[-1]))
            except Exception:
                pass
    nxt = (max(nums) + 1) if nums else 1
    return f"P-{year}-{nxt:03d}"

def _capacity_suggested_start(dfp: pd.DataFrame, start_after: date | None = None, capacity:int = 5) -> date:
    if start_after is None:
        start_after = date.today()
    sdt = pd.to_datetime(dfp.get("start"), errors="coerce").dt.date if not dfp.empty else pd.Series([], dtype="object")
    edt = pd.to_datetime(dfp.get("end"), errors="coerce").dt.date   if not dfp.empty else pd.Series([], dtype="object")
    probe = start_after
    for _ in range(365):
        active = int(((sdt <= probe) & (edt >= probe)).sum()) if not dfp.empty else 0
        if active < capacity:
            return probe
        probe += timedelta(days=1)
    return start_after

def _maps_links(address: str, pasted_url: str | None = None) -> Tuple[str, str]:
    if pasted_url and pasted_url.strip():
        return pasted_url.strip(), pasted_url.strip()
    q = quote_plus(address.strip())
    return (f"https://www.google.com/maps/search/?api=1&query={q}",
            f"https://waze.com/ul?ll&navigate=yes&q={q}")

def _save_attachments(files, proj_id: str, section: str | None = None) -> list[str]:
    saved = []
    if not files:
        return saved
    target = ATTACH_DIR / proj_id / (section or "_general")
    target.mkdir(parents=True, exist_ok=True)
    for f in files:
        fname = f.name.replace("/", "_").replace("\\", "_")
        with open(target / fname, "wb") as out:
            out.write(f.getbuffer())
        saved.append(str((target / fname).relative_to(APP_ROOT)))
    return saved

def _preview_upload(file):
    if not file:
        return
    name = file.name.lower()
    if any(name.endswith(ext) for ext in (".png",".jpg",".jpeg",".webp")):
        st.image(file, caption=file.name, use_container_width=True)
    elif name.endswith(".pdf"):
        b64 = base64.b64encode(file.getvalue()).decode("utf-8")
        st.markdown(
            f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="340" style="border:1px solid #bbb;border-radius:8px;"></iframe>',
            unsafe_allow_html=True,
        )
    else:
        st.info(f"Fișier încărcat: {file.name}")

def _offers_cols() -> List[str]:
    return ["id","company","project","value","offer_date","valid_until","extended_days","status","accepted_date"]

def _append_offer(rec: dict):
    try:
        df = pd.read_excel(OFFERS_XLSX, sheet_name="Oferte", engine="openpyxl")
    except Exception:
        df = pd.DataFrame(columns=_offers_cols())
    for c in _offers_cols():
        if c not in df.columns:
            df[c] = None
    row = pd.DataFrame([rec])
    df = pd.concat([df, row], ignore_index=True)
    with pd.ExcelWriter(OFFERS_XLSX, engine="openpyxl", mode="w") as xlw:
        df[_offers_cols()].to_excel(xlw, sheet_name="Oferte", index=False)

def _update_offer_status(proj_id: str, status: str, accepted_date: date | None = None):
    try:
        df = pd.read_excel(OFFERS_XLSX, sheet_name="Oferte", engine="openpyxl")
    except Exception:
        return
    if "id" not in df.columns:
        return
    mask = df["id"].astype(str) == str(proj_id)
    if not mask.any():
        return
    df.loc[mask, "status"] = status
    if accepted_date:
        df.loc[mask, "accepted_date"] = accepted_date.isoformat()
    with pd.ExcelWriter(OFFERS_XLSX, engine="openpyxl", mode="w") as xlw:
        df[_offers_cols()].to_excel(xlw, sheet_name="Oferte", index=False)

# ---------- Configurator ofertă: calc ore/zile + volum/mașină ----------
def _compute_from_config(config: List[dict], delivery_type: str) -> Tuple[Dict[str, int], float, float, str]:
    """
    Returnează:
      - durations_days: {secție: zile}
      - total_volume_m3 (considerând tipul de livrare)
      - needed_height_m (înălțime utilă minimă)
      - vehicle_hint (string)
    """
    sec_hours: Dict[str, float] = {}
    total_vol_m3 = 0.0
    needed_h_m = 0.0

    for it in config:
        typ = it["type"]
        H = max(float(it.get("H", 0)), 0.0) / 1000.0  # m
        L = max(float(it.get("L", 0)), 0.0) / 1000.0
        D = max(float(it.get("D", 0)), 0.0) / 1000.0
        units = max(int(it.get("units", 1)), 1)

        if typ == "Dressing":
            # lungime totală (mm) și adâncime D; estimăm module de 0.8m
            length_total_m = max(float(it.get("length_total", 0)), 0.0) / 1000.0
            module_w = 0.8  # m
            units = max(1, ceil(length_total_m / module_w))
            # H poate fi personalizat; dacă lipsește, estimăm 2.4m
            if H <= 0:
                H = 2.4
            L = module_w  # lățimea medie a unui modul pentru volum/ front
            # volum continuu
            vol = length_total_m * D * H
        else:
            # Dulap simplu sau alte tipuri „unit”
            if H <= 0: H = 2.0
            if L <= 0: L = 0.8
            if D <= 0: D = 0.6
            vol = H * L * D * units

        # Materiale (procente fronturi vopsite / furnir)
        paint_pct = max(min(int(it.get("paint_pct", 0)), 100), 0)
        veneer_pct = max(min(int(it.get("veneer_pct", 0)), 100), 0)
        # suprafață front estimată: H x (L * units) sau H x lungime_dressing
        if typ == "Dressing":
            length_total_m = max(float(it.get("length_total", 0)), 0.0) / 1000.0
            front_area_m2 = H * length_total_m
        else:
            front_area_m2 = H * L * units

        # Ore de bază per unitate (dulap) -> scale cu units
        for sec, hpu in BASE_HOURS_PER_UNIT.items():
            sec_hours[sec] = sec_hours.get(sec, 0.0) + hpu * units

        # Vopsitorie & Pregătire (raport cu % vopsit)
        if paint_pct > 0 and front_area_m2 > 0:
            share = paint_pct / 100.0
            sec_hours["Pregătire vopsitorie"] = sec_hours.get("Pregătire vopsitorie", 0.0) + PAINT_PREP_H_PER_M2 * front_area_m2 * share
            sec_hours["Vopsitorie"] = sec_hours.get("Vopsitorie", 0.0) + PAINT_COAT_H_PER_M2 * front_area_m2 * share

        # Furnir (raport cu % furnir)
        if veneer_pct > 0 and front_area_m2 > 0:
            share = veneer_pct / 100.0
            sec_hours["Furnir"] = sec_hours.get("Furnir", 0.0) + VENEER_H_PER_M2 * front_area_m2 * share

        # volum + înălțime necesară (pentru vehicul)
        total_vol_m3 += vol
        needed_h_m = max(needed_h_m, H)

    # Ajustări livrare
    assembled = (delivery_type == "Asamblate")
    vol_factor = 1.0 if assembled else VOLUME_REDUCTION_DEZASAMBLAT
    pack_factor = PACK_FACTOR_ASAMBLAT if assembled else PACK_FACTOR_DEZASAMBLAT
    total_vol_m3 *= vol_factor

    # Ambalare suplimentară
    pack_hours = PACK_BASE_H + PACK_H_PER_M3 * total_vol_m3 * pack_factor
    sec_hours["Ambalare"] = sec_hours.get("Ambalare", 0.0) + pack_hours

    # Vehicul recomandat
    if total_vol_m3 < 3:
        vehicle = "Autoutilitară mică (≈3 m³)"
    elif total_vol_m3 < 6:
        vehicle = "Van mediu (≈6 m³)"
    elif total_vol_m3 < 12:
        vehicle = "Van mare (≈12 m³)"
    elif total_vol_m3 < 20:
        vehicle = "Camion 3.5T (≈20 m³)"
    else:
        vehicle = "Camion >7.5T"

    # Transformăm ore -> zile (ținând cont de capacități)
    durations_days: Dict[str, int] = {}
    for sec, hours in sec_hours.items():
        cap = max(SEC_CAPACITY_HPD.get(sec, 8), 1)
        durations_days[sec] = max(1, ceil(hours / cap))

    return durations_days, round(total_vol_m3, 2), round(needed_h_m, 2), vehicle

def _deadlines_from_durations(start_dt: date, sections: List[str], durations_override: Optional[Dict[str, int]] = None) -> Tuple[dict, date]:
    d: Dict[str, date] = {}
    cur = start_dt
    for sec in sections:
        dur_days = (durations_override or {}).get(sec, NORM_DAYS_FALLBACK.get(sec, 1))
        fin = cur + timedelta(days=max(int(dur_days), 1))
        d[sec] = fin
        cur = fin
    end_dt = max(d.values()) if d else start_dt
    return d, end_dt

# ---------- UI principal ----------
def render(ctx=None, **kwargs):
    # CSS compact
    st.markdown("""
    <style>
      .small-card{border:1px solid #dcdcdc;border-radius:10px;padding:8px;margin-bottom:8px;background:#fffef8;}
      .tight .stSlider, .tight .stDateInput, .tight .stTextInput, .tight .stNumberInput, .tight .stTextArea{margin-top:0.05rem;margin-bottom:0.05rem;}
      .tight input, .tight textarea{font-size:0.92rem;}
      .tight label p{margin-bottom:0.1rem;}
      .summary{padding:8px;border:1px dashed #cfcfcf;border-radius:10px;background:#fffffa;margin:6px 0;}
      .btn-row a{margin-right:8px;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("## 🧾 Comandă nouă (Ofertă ➜ Proiect)")
    dfp = data.projects.copy()
    dfu = data.users.copy()

    proj_id = st.session_state.get("new_proj_id") or _next_project_id(dfp)
    st.session_state["new_proj_id"] = proj_id

    # ====== ETAPA 1: OFERTĂ ======
    with st.expander("1) ✍️ Ofertă nouă", expanded=not st.session_state.get("offer_validated", False)):
        c1,c2,c3,c4 = st.columns([2,2,1.2,1.2])
        with c1: company = st.text_input("Companie", st.session_state.get("offer_company",""))
        with c2: project_name = st.text_input("Nume proiect", st.session_state.get("offer_project",""))
        with c3: offer_value = st.number_input("Valoare ofertă (RON)", min_value=0.0, step=100.0, value=float(st.session_state.get("offer_value",0)))
        with c4: valid_days  = st.number_input("Validitate (zile)", min_value=1, max_value=60, value=int(st.session_state.get("offer_days",5)))
        offer_date = st.date_input("Data ofertei", value=st.session_state.get("offer_date", date.today()))
        valid_until = offer_date + timedelta(days=int(valid_days))
        st.caption(f"📌 Ofertă valabilă până la **{valid_until.isoformat()}** (extensibil).")

        # --- Setări complexe (Configurator mobilier) ---
        st.markdown("#### ⚙️ Setări complexe ofertă")
        adv = st.toggle("Activează configurator tipuri de mobilier", value=False, key="offer_adv")
        if adv:
            if "offer_config" not in st.session_state:
                st.session_state.offer_config = []
            if "offer_delivery" not in st.session_state:
                st.session_state.offer_delivery = "Asamblate"

            st.radio("Tip livrare", options=["Asamblate","Dezasamblate"], index=0 if st.session_state.offer_delivery=="Asamblate" else 1, key="offer_delivery", horizontal=True)

            # formular item
            available = ["Dulap simplu", "Dressing", "Corp bucătărie", "Front MDF vopsit", "Blat", "Polițe/rafturi"]
            colA, colB, colC, colD, colE, colF = st.columns([1.4,1,1,1,1,1.2])
            with colA:
                typ = st.selectbox("Tip", available, key="sel_typ")
            with colB:
                units = st.number_input("Bucăți", min_value=1, value=1, step=1, key="sel_units")
            with colC:
                H = st.number_input("Înălțime (mm)", min_value=0, value=2400 if st.session_state.sel_typ != "Blat" else 40, step=10, key="sel_h")
            with colD:
                L = st.number_input("Lățime/Lungime (mm)", min_value=0, value=800, step=10, key="sel_l")
            with colE:
                D = st.number_input("Adâncime (mm)", min_value=0, value=600, step=10, key="sel_d")
            with colF:
                length_total = st.number_input("Lungime totală (mm) (Dressing)", min_value=0, value=3000, step=50, key="sel_length")

            # materiale fronturi
            mc1, mc2, mc3 = st.columns([1,1,1])
            with mc1:
                mat_paint = st.checkbox("Fronturi vopsite (MDF)", value=False, key="mat_paint")
                paint_pct = st.number_input("Procent vopsite (%)", min_value=0, max_value=100, value=100 if mat_paint else 0, key="paint_pct")
            with mc2:
                mat_veneer = st.checkbox("Fronturi furnir", value=False, key="mat_veneer")
                veneer_pct = st.number_input("Procent furnir (%)", min_value=0, max_value=100, value=0 if mat_paint else 100 if mat_veneer else 0, key="veneer_pct")
            with mc3:
                if paint_pct + veneer_pct > 100:
                    st.warning("Procentele de materiale depășesc 100%.")

            if st.button("➕ Adaugă componentă"):
                rec = {
                    "type": st.session_state.sel_typ,
                    "units": units,
                    "H": H, "L": L, "D": D,
                    "length_total": length_total if st.session_state.sel_typ == "Dressing" else 0,
                    "mat_paint": mat_paint, "paint_pct": paint_pct,
                    "mat_veneer": mat_veneer, "veneer_pct": veneer_pct,
                }
                st.session_state.offer_config.append(rec)
                st.success("Componentă adăugată în configurator.")

            if st.session_state.offer_config:
                st.table(pd.DataFrame(st.session_state.offer_config))

                # calculează durate + volum + mașină
                dur_map, vol_m3, need_h, veh = _compute_from_config(
                    st.session_state.offer_config, st.session_state.offer_delivery
                )
                st.session_state["durations_override"] = dur_map
                st.session_state["sim_vehicle"] = f"{veh} | Volum estimat: {vol_m3} m³ | Înălțime utilă minimă: {need_h} m"
                st.info(st.session_state["sim_vehicle"])
                if dur_map:
                    st.caption("Durate estimate (zile) per secție (din configurator): " + ", ".join(f"{k}: {v}" for k,v in dur_map.items()))

        # validare ofertă
        cc1, cc2, cc3 = st.columns([1.4,1,1])
        with cc1: validate_offer = st.button("✅ Validează oferta")
        with cc2: extend = st.number_input("Extinde cu (zile)", min_value=0, max_value=30, value=0)
        with cc3: apply_ext = st.button("↗️ Aplică extinderea")

        if apply_ext:
            valid_until = valid_until + timedelta(days=int(extend))
            st.session_state["offer_days"] = valid_days + int(extend)
            st.success(f"Valabilitate extinsă până la {valid_until.isoformat()}")

        if validate_offer:
            st.session_state.update({
                "offer_validated": True,
                "offer_company": company,
                "offer_project": project_name,
                "offer_value": offer_value,
                "offer_days": valid_days,
                "offer_date": offer_date,
            })
            _append_offer({
                "id": proj_id, "company": company, "project": project_name,
                "value": float(offer_value), "offer_date": offer_date.isoformat(),
                "valid_until": (offer_date + timedelta(days=int(valid_days))).isoformat(),
                "extended_days": 0, "status": "Pending", "accepted_date": None,
            })
            st.info("Ofertă salvată ca **Pending**. Continuă cu etapa 2.")

    if st.session_state.get("offer_validated", False):
        oc, op, ov = st.columns([2,2,1.2])
        oc.success(f"Ofertă: {st.session_state['offer_company']}")
        op.success(f"Proiect: {st.session_state['offer_project']}")
        ov.success(f"Valoare: {float(st.session_state['offer_value']):,.2f} RON".replace(",", " "))

    # ====== ETAPA 2: PROIECT ======
    with st.expander("2) 🏗️ Proiect (Comandă nouă)", expanded=True):
        left, right = st.columns(2)

        # —— Stânga: client + PM + financiar/tranșe (selector radio 1–4) ——
        with left:
            st.markdown("### 👤 Date client")
            client_name = st.text_input("Persoană de contact client", key="client_name")
            client_email = st.text_input("Email client", key="client_email")
            client_phone = st.text_input("Telefon client", key="client_phone")

            st.markdown("### 🧑‍💼 Project Manager")
            pm_opts = dfu["name"].astype(str).tolist() if not dfu.empty else [""]
            pm_default = 0
            if not dfu.empty:
                roles = dfu[["name","role"]].astype(str)
                managers = roles[roles["role"].str.lower().str.contains("manager", na=False)]["name"].tolist()
                if managers and managers[0] in pm_opts:
                    pm_default = pm_opts.index(managers[0])
            project_manager = st.selectbox("Alege Project Manager-ul", options=pm_opts, index=pm_default)

            st.markdown("### 💳 Financiar & tranșe")
            value = st.number_input("Valoare totală (RON)", min_value=0.0, step=100.0, value=float(st.session_state.get("offer_value",0)))
            # ⇩ selector radio 1–4 (nu slider, nu input manual)
            n_tr = st.radio("Număr tranșe", options=[1,2,3,4], index=3, horizontal=True, key="rt_ntr")
            reco = RECO_SPLITS.get(int(n_tr), RECO_SPLITS[4]).copy()
            keyp = f"percents_{int(n_tr)}"
            if keyp not in st.session_state or len(st.session_state[keyp]) != int(n_tr):
                st.session_state[keyp] = reco

            cols = st.columns(int(n_tr))
            percents, t_amounts, t_dates, t_due, t_paid, t_extdays = [], [], [], [], [], []
            for i, col in enumerate(cols):
                with col:
                    st.markdown('<div class="small-card tight">', unsafe_allow_html=True)
                    p = st.number_input(f"T{i+1} (%)", min_value=0, max_value=100, value=int(st.session_state[keyp][i]), key=f"tr_p_{i}")
                    percents.append(p)
                    amt = round(value * (p / 100.0), 2) if value else 0.0
                    t_amounts.append(amt)
                    st.write(f"**{amt:,.2f} RON**".replace(",", " "))
                    inv_date = st.date_input(f"Data factură T{i+1}", key=f"tr_inv_{i}", value=date.today())
                    ext = st.number_input(f"Extindere scadență (zile) T{i+1}", min_value=0, max_value=30, value=0, key=f"tr_ext_{i}")
                    due = inv_date + timedelta(days=1 + ext)
                    st.caption(f"Scadență: **{due.isoformat()}**")
                    paid = st.checkbox(f"Plătită T{i+1}?", key=f"tr_paid_{i}", value=False)
                    t_dates.append(inv_date); t_due.append(due); t_paid.append(paid); t_extdays.append(ext)
                    st.markdown('</div>', unsafe_allow_html=True)

            sum_df = pd.DataFrame({
                "Tranșa": [f"T{i+1}" for i in range(int(n_tr))],
                "%": percents, "Valoare": t_amounts,
                "Factură": [d.isoformat() for d in t_dates],
                "Scadență": [d.isoformat() for d in t_due],
                "Plătită": ["da" if p else "nu" for p in t_paid],
            })
            st.dataframe(sum_df, use_container_width=True, height=140)
            if sum(percents) != 100:
                st.warning(f"Procentele însumează {sum(percents)}% (trebuie 100%).")

        # —— Dreapta: livrare/montaj + planificare (+ butoane link) ——
        with right:
            st.markdown("### 📍 Livrare / Montaj")
            address = st.text_area("Adresă proiect / livrare", placeholder="Stradă, nr., oraș, județ", height=92)
            floor_enabled = st.checkbox("Montaj la etaj (≠ parter 0)?", value=False)
            floor = st.slider("Etaj", -2, 20, 0, disabled=not floor_enabled)
            install_contact = st.text_input("Persoană contact montaj", "")
            install_phone = st.text_input("Telefon contact montaj", "")
            paste_map = st.text_input("Link share (Waze/Google Maps) — opțional", "")

            gmaps, waze = ("","")
            if address.strip() or paste_map.strip():
                gmaps, waze = _maps_links(address, pasted_url=paste_map)

            # Butoane dedicate pentru direcții (cu fallback)
            try:
                st.link_button("📍 Deschide Google Maps", gmaps, use_container_width=True)
                st.link_button("🧭 Deschide Waze", waze, use_container_width=True)
            except Exception:
                st.markdown(f'<div class="btn-row"><a href="{gmaps}" target="_blank">📍 Deschide Google Maps</a> <a href="{waze}" target="_blank">🧭 Deschide Waze</a></div>', unsafe_allow_html=True)

            st.markdown("### 🗓️ Planificare & resurse")
            contract_date = st.date_input("Data semnării contractului", value=date.today())
            production_start = st.date_input("Data intrării în producție", value=date.today())
            suggested = _capacity_suggested_start(dfp, start_after=contract_date)
            cc1, cc2 = st.columns([1,1])
            with cc1: st.caption(f"Start sugerat: **{suggested.isoformat()}**")
            with cc2:
                if st.button("Folosește start sugerat"):
                    production_start = suggested
                    st.experimental_rerun()

        # ===== Secții: comportament „ultima deschisă sus” & colaps după salvare (din iterația precedentă) =====
        st.markdown("### 🏭 Secții alocate, progres & documente")

        if "selected_sections" not in st.session_state:
            st.session_state.selected_sections = []
        if "toggle_prev" not in st.session_state:
            st.session_state.toggle_prev = {s: False for s in SECTIONS}
        if "sec_notes" not in st.session_state:
            st.session_state.sec_notes = {}
        if "sec_participants" not in st.session_state:
            st.session_state.sec_participants = {}
        if "sec_collapsed" not in st.session_state:
            st.session_state.sec_collapsed = {}

        row1 = SECTIONS[: len(SECTIONS)//2]
        row2 = SECTIONS[len(SECTIONS)//2 :]

        def _toggle_row(opts: List[str]):
            cols = st.columns(len(opts))
            picked = set(st.session_state.selected_sections)
            recent_opened = None
            for i, sec in enumerate(opts):
                with cols[i]:
                    new_val = st.toggle(sec, value=(sec in picked), key=f"sec_{sec}")
                    if new_val and not st.session_state.toggle_prev.get(sec, False):
                        recent_opened = sec
                        picked.add(sec)
                    elif (not new_val) and st.session_state.toggle_prev.get(sec, False):
                        picked.discard(sec)
                        st.session_state.sec_collapsed.pop(sec, None)
                st.session_state.toggle_prev[sec] = new_val

            lst = [s for s in st.session_state.selected_sections if s in picked]
            for s in picked:
                if s not in lst:
                    lst.append(s)
            if recent_opened and recent_opened in lst:
                lst.remove(recent_opened)
                lst.insert(0, recent_opened)
            st.session_state.selected_sections = lst

        _toggle_row(row1); _toggle_row(row2)
        selected_sections = st.session_state.selected_sections

        progress_map: Dict[str, int] = {}
        for sec in selected_sections:
            collapsed = st.session_state.sec_collapsed.get(sec, False)
            cur_prog = st.session_state.get(f"prog_{sec}", 0)
            parts_cur = st.session_state.sec_participants.get(sec, [])
            header = f"{sec} — {cur_prog}% — participanți: {', '.join(parts_cur) if parts_cur else '—'}"
            with st.expander(header, expanded=not collapsed):
                # 3 coloane pentru compactare & vizibilitate clară
                c1, c2, c3 = st.columns([1,1,1])
                with c1:
                    progress_map[sec] = st.slider(f"Progres {sec} (%)", 0, 100, st.session_state.get(f"prog_{sec}", 0), key=f"prog_{sec}")
                    sec_people = dfu[dfu["section"].astype(str) == sec]["name"].dropna().astype(str).tolist() if not dfu.empty else []
                    current = st.session_state.sec_participants.get(sec, sec_people)
                    sec_part = st.multiselect(f"Coparticipanți {sec}", options=dfu["name"].astype(str).tolist() if not dfu.empty else [], default=current, key=f"part_{sec}")
                with c2:
                    note = st.text_area(f"Adnotare ({sec})", key=f"note_{sec}", height=100, placeholder="Observații…")
                    files = st.file_uploader(f"Documente ({sec})", type=["png","jpg","jpeg","webp","pdf"], accept_multiple_files=True, key=f"up_{sec}")
                with c3:
                    visible_all = st.checkbox("Vizibil pentru toate secțiile", value=False, key=f"vis_{sec}")
                    if files:
                        for f in files: _preview_upload(f)
                    if st.button(f"💾 Salvează modificări {sec}", key=f"save_{sec}"):
                        saved = _save_attachments(files, proj_id, section=sec)
                        entry = {"note": note.strip(), "all": bool(visible_all), "files": saved}
                        st.session_state.sec_notes.setdefault(sec, []).append(entry)
                        st.session_state.sec_participants[sec] = sec_part
                        st.session_state.sec_collapsed[sec] = True
                        st.success("Modificări salvate (panoul s-a pliat).")
                        st.experimental_rerun()

        if selected_sections:
            avg_prog = round(sum(st.session_state.get(f"prog_{s}", 0) for s in selected_sections) / max(len(selected_sections),1), 1)
            st.info(f"Progres general (medie secții selectate): **{avg_prog}%**")

        # ---- Simulare de producție (calendar / Gantt) înainte de Salvare ----
        st.markdown("### 🗓️ Simulare de producție")
        if st.button("🔮 Simulează programarea"):
            # preferăm duratele din configurator dacă există
            dur_override = st.session_state.get("durations_override", {})
            # păstrăm doar secțiile selectate
            dur_usable = {k:v for k,v in dur_override.items() if k in selected_sections} if dur_override else {}

            sec_deadlines, end_dt = _deadlines_from_durations(
                production_start, selected_sections, durations_override=dur_usable if dur_usable else None
            )

            sched = pd.DataFrame({
                "section": list(sec_deadlines.keys()),
                "start": [production_start] + list(pd.to_datetime(list(sec_deadlines.values())).date[:-1]) if len(sec_deadlines)>0 else [],
                "end": list(sec_deadlines.values()),
            })
            if not sched.empty and alt is not None:
                chart = alt.Chart(sched).mark_bar().encode(
                    x="start:T", x2="end:T",
                    y=alt.Y("section:N", sort=None, title="Secție"),
                    tooltip=[alt.Tooltip("section:N", title="Secție"), alt.Tooltip("start:T"), alt.Tooltip("end:T")]
                ).properties(width="container", height=28*max(1, len(sched)))
                st.altair_chart(chart, use_container_width=True)
            else:
                st.dataframe(sched, use_container_width=True, height=200)

            st.session_state["simulated_deadlines"] = {k: v.isoformat() for k, v in sec_deadlines.items()}
            st.success(f"Simulare finalizată. Termen final estimat: **{end_dt.isoformat()}**")

        if st.session_state.get("simulated_deadlines"):
            with st.expander("🗂️ Programare simulată (detalii)", expanded=False):
                st.json(st.session_state["simulated_deadlines"])

        # ---- Note generale + galerie globală (fișiere ALL) ----
        st.markdown("### 📝 Note generale & atașamente")
        notes_general = st.text_area("Note proiect (opțional)", height=80)
        uploads_general = st.file_uploader("Documente generale", type=["png","jpg","jpeg","webp","pdf"], accept_multiple_files=True, key="up_general")
        if uploads_general:
            for f in uploads_general: _preview_upload(f)

        global_files: List[str] = []
        for entries in st.session_state.sec_notes.values():
            for e in entries:
                if e.get("all"):
                    global_files.extend(e.get("files", []))
        if global_files:
            st.markdown("### 📷 Galerie globală (vizibilă tuturor secțiilor)")
            for fp in global_files[:10]:
                try:
                    full = (APP_ROOT / fp).resolve()
                    if str(full).lower().endswith((".png",".jpg",".jpeg",".webp")):
                        st.image(str(full), use_container_width=True)
                    elif str(full).lower().endswith(".pdf"):
                        with open(full, "rb") as fh:
                            b64 = base64.b64encode(fh.read()).decode("utf-8")
                        st.markdown(
                            f'<iframe src="data:application/pdf;base64,{b64}" width="100%" height="300" style="border:1px solid #bbb;border-radius:8px;"></iframe>',
                            unsafe_allow_html=True,
                        )
                except Exception:
                    st.write(fp)

        st.markdown("---")
        save = st.button("💾 Salvează proiect")

        if save:
            errs = []
            if not st.session_state.get("offer_validated", False): errs.append("Validează mai întâi **Oferta**.")
            if not st.session_state.get("offer_company","").strip(): errs.append("Compania lipsește (din ofertă).")
            if not st.session_state.get("offer_project","").strip(): errs.append("Numele proiectului lipsește (din ofertă).")
            if value <= 0: errs.append("Valoarea totală trebuie să fie > 0.")
            if not selected_sections: errs.append("Selectează cel puțin o secție.")
            percents = [st.session_state.get(f"tr_p_{i}", 0) for i in range(int(n_tr))]
            if sum(percents) != 100: errs.append("Procentele tranșelor trebuie să însumeze 100%.")
            if errs:
                st.error("• " + "\n• ".join(errs)); st.stop()

            # Id final după fișier
            try:
                dfp_latest = pd.read_excel(PROJECTS_XLSX, sheet_name="Proiecte", engine="openpyxl")
            except Exception:
                dfp_latest = pd.DataFrame(columns=PROJECT_COLS_ORDER)
            proj_id = _next_project_id(dfp_latest)

            # durate/termene: preferăm simularea/ configuratorul
            dur_override = st.session_state.get("durations_override", {})
            dur_usable = {k:v for k,v in dur_override.items() if k in selected_sections} if dur_override else {}
            sec_deadlines, end_dt = _deadlines_from_durations(
                production_start, selected_sections, durations_override=dur_usable if dur_usable else None
            )
            deadlines_str = "; ".join(f"{k}: {v.isoformat()}" for k, v in sec_deadlines.items())
            sections_str = ", ".join(selected_sections)
            sections_prog_str = ", ".join(str(st.session_state.get(f"prog_{s}",0)) for s in selected_sections)
            progress_overall = round(sum(st.session_state.get(f"prog_{s}",0) for s in selected_sections)/max(len(selected_sections),1),1)

            # tranșe → inst
            inst_flags = ["nu"] * 4
            inst_amts  = [0.0] * 4
            for i in range(min(int(n_tr),4)):
                inst_flags[i] = "da"
                inst_amts[i] = round(float(value) * (float(percents[i]) / 100.0), 2)

            saved_general = _save_attachments(uploads_general, proj_id, section=None)

            # manifest secții
            sec_manifest_lines = []
            for sec, entries in st.session_state.sec_notes.items():
                parts = st.session_state.sec_participants.get(sec, [])
                parts_str = ", ".join(parts)
                for e in entries:
                    files_str = ", ".join(e.get("files", []))
                    sec_manifest_lines.append(
                        f"[SEC:{sec}][ALL:{int(e.get('all', False))}][PART:{parts_str}] {e.get('note','').strip()} | FILES: {files_str}"
                    )
            sec_manifest = "\n".join(sec_manifest_lines)
            sim_vehicle = st.session_state.get("sim_vehicle","")

            new_row = {
                "id": proj_id,
                "name": st.session_state["offer_project"],
                "company": st.session_state["offer_company"],
                "contact_name": client_name,
                "contact_email": client_email,
                "contact_phone": client_phone,
                "address": address,
                "floor": floor if floor_enabled else 0,
                "install_contact": f"{install_contact} / {install_phone}".strip(" /"),
                "responsible": project_manager,
                "participants": ", ".join(sorted({p for arr in st.session_state.sec_participants.values() for p in arr})),
                "value": float(value),
                "inst1": inst_flags[0], "inst2": inst_flags[1], "inst3": inst_flags[2], "inst4": inst_flags[3],
                "inst1_amount": inst_amts[0], "inst2_amount": inst_amts[1], "inst3_amount": inst_amts[2], "inst4_amount": inst_amts[3],
                "sections": sections_str,
                "sections_progress": sections_prog_str,
                "section_deadlines": deadlines_str,
                "progress_overall": progress_overall,
                "status": 50,
                "start": production_start.isoformat(),
                "end": end_dt.isoformat(),
                "notes": (
                    f"PM: {project_manager}\n"
                    + (sim_vehicle + "\n" if sim_vehicle else "")
                    + f"MANIFEST:\n{sec_manifest}\n"
                    + (f"GLOBAL_FILES: {', '.join(global_files)}\n" if global_files else "")
                    + (f"GENERAL_FILES: {', '.join(saved_general)}" if saved_general else "")
                ).strip(),
            }

            row_df = pd.DataFrame([new_row])
            for c in PROJECT_COLS_ORDER:
                if c not in row_df.columns:
                    row_df[c] = None
            row_df = row_df[PROJECT_COLS_ORDER]

            try:
                full_df = pd.read_excel(PROJECTS_XLSX, sheet_name="Proiecte", engine="openpyxl")
            except Exception:
                full_df = pd.DataFrame(columns=PROJECT_COLS_ORDER)
            full_df = pd.concat([full_df, row_df], ignore_index=True)
            with pd.ExcelWriter(PROJECTS_XLSX, engine="openpyxl", mode="w") as xlw:
                full_df.to_excel(xlw, sheet_name="Proiecte", index=False)

            _update_offer_status(proj_id, status="Accepted", accepted_date=date.today())
            for k in ["sec_notes","sec_participants","durations_override","simulated_deadlines","sim_vehicle"]:
                st.session_state.pop(k, None)
            st.success(f"Proiectul **{proj_id}** a fost salvat, iar oferta marcată **Accepted**.")
            data.refresh()
