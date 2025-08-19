# containers/help.py
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import List, Dict

import pandas as pd
import streamlit as st

from utils.data_loader import DATA_DIR

HELP_PATH = DATA_DIR / "ritmuri.csv"
HELP_PATH.parent.mkdir(parents=True, exist_ok=True)

SECTIONS = [
    "Ofertare", "Proiectare & Design", "Tehnologică", "Achiziții", "CNC",
    "Debitare", "Furnir", "Pregătire vopsitorie", "Vopsitorie",
    "CTC", "Ambalare", "Transport (Livrare)", "Montaj"
]

DEFAULT_RATES: List[Dict] = [
    # section, metric, unit, rate, note
    {"section":"Ofertare", "metric":"timp mediu ofertă", "unit":"ore/proiect", "rate":2.0, "note":"calcul preț + transmitere client"},
    {"section":"Proiectare & Design", "metric":"proiectare mobilier", "unit":"ore/mp", "rate":1.5, "note":"schițe tehnice"},
    {"section":"Proiectare & Design", "metric":"randare opțională", "unit":"ore/proiect", "rate":4.0, "note":"opțional"},
    {"section":"Tehnologică", "metric":"programare CNC", "unit":"ore/mp", "rate":0.5, "note":"drill/router"},
    {"section":"Tehnologică", "metric":"fișe tehnice", "unit":"ore/proiect", "rate":1.0, "note":""},
    {"section":"Achiziții", "metric":"lead time standard", "unit":"zile", "rate":3.0, "note":"medie furnizori"},
    {"section":"Achiziții", "metric":"plasare comenzi", "unit":"ore/proiect", "rate":1.0, "note":""},
    {"section":"CNC", "metric":"prelucrare panouri", "unit":"mp/oră", "rate":8.0, "note":"standard"},
    {"section":"CNC", "metric":"găurire specială", "unit":"buc/oră", "rate":60.0, "note":"fixtures"},
    {"section":"Debitare", "metric":"debitare panouri", "unit":"mp/oră", "rate":20.0, "note":""},
    {"section":"Furnir", "metric":"presare furnir", "unit":"mp/oră", "rate":6.0, "note":""},
    {"section":"Furnir", "metric":"calibrare", "unit":"mp/oră", "rate":8.0, "note":""},
    {"section":"Pregătire vopsitorie", "metric":"șlefuire/pregătire", "unit":"mp/oră", "rate":10.0, "note":""},
    {"section":"Vopsitorie", "metric":"aplicare finisaj", "unit":"mp/oră", "rate":6.0, "note":"1-2 straturi"},
    {"section":"Vopsitorie", "metric":"uscare", "unit":"ore/ciclu", "rate":2.0, "note":"cabina"},
    {"section":"CTC", "metric":"verificare calitate", "unit":"buc/oră", "rate":30.0, "note":"vizual + măsurare"},
    {"section":"Ambalare", "metric":"ambalare module", "unit":"buc/oră", "rate":15.0, "note":""},
    {"section":"Ambalare", "metric":"ambalare panouri", "unit":"mp/oră", "rate":12.0, "note":""},
    {"section":"Transport (Livrare)", "metric":"încărcare", "unit":"m³/oră", "rate":20.0, "note":""},
    {"section":"Transport (Livrare)", "metric":"livrare urban", "unit":"km/oră", "rate":25.0, "note":""},
    {"section":"Montaj", "metric":"montaj mobilier standard", "unit":"mp/oră", "rate":2.0, "note":"2 oameni"},
    {"section":"Montaj", "metric":"montaj dressing", "unit":"ml/oră", "rate":1.2, "note":"2 oameni"},
]

COLS = ["section","metric","unit","rate","note"]

def _load_rates() -> pd.DataFrame:
    if HELP_PATH.exists():
        try:
            df = pd.read_csv(HELP_PATH)
            for c in COLS:
                if c not in df.columns:
                    df[c] = ""
            df["rate"] = pd.to_numeric(df["rate"], errors="coerce").fillna(0.0)
            return df[COLS].copy()
        except Exception:
            pass
    return pd.DataFrame(DEFAULT_RATES, columns=COLS)

def _save_rates(df: pd.DataFrame):
    out = df.copy()
    for c in COLS:
        if c not in out.columns:
            out[c] = ""
    out["rate"] = pd.to_numeric(out["rate"], errors="coerce").fillna(0.0)
    out[COLS].to_csv(HELP_PATH, index=False)

def _feature_list():
    st.markdown("### Funcționalități pe pagini")
    st.markdown(
        """
- **Dashboard** – KPI-uri rapide (active, întârziate, valoare totală), tabel proiecte, distribuție pe secții și prognoză finalizări.
- **Vedere generală** – listă proiecte + utilizatori (overview rapid).
- **Secțiuni (Board operator)** – pipeline super-compact pentru fiecare secție pe proiect; progres dinamic per secție; adnotări; fișiere atașate; istoric; responsabil + coparticipanți; jurnal modificări.
- **Profil utilizator** – avatar/nume/rol/secție + proiectele aferente secției utilizatorului.
- **Comandă nouă** – ofertă rapidă + crearea proiectului; setări de bază (client, contact, adresă, date planificare, secții alocate).
- **Utilizatori** – listă editabilă, adăugare rapidă, import/export, roluri & permisiuni (simplificat).
- **Verificare date** – (opțional) controale de consistență și diagnostic.
- **Ajutor** – descrierea secțiilor și *Ritmuri pe secțiuni* (norme editabile, persistente).
        """
    )
    st.divider()
    st.markdown("### Descriere pe secțiuni de producție")
    st.markdown(
        """
**1. Ofertare** – colectează cerințele, calculează costuri, generează ofertă și urmărește validarea.  
**2. Proiectare & Design** – modele, desene tehnice, eventual randări; pregătire pentru tehnologică.  
**3. Tehnologică** – programe CNC, fișe tehnice, liste piese, optimizări.  
**4. Achiziții** – comenzi materiale/accesorii, urmărire termene, recepție.  
**5. CNC** – găurire/rutare/conturare conform programelor.  
**6. Debitare** – debit panouri, optimizare tăiere.  
**7. Furnir** – presare/laminare, calibrare.  
**8. Pregătire vopsitorie** – șlefuire, chituire, pregătire suprafețe.  
**9. Vopsitorie** – aplicare finisaj, uscare, control aspect.  
**10. CTC** – verificare dimensională/estetică, avizare.  
**11. Ambalare** – protecție, etichetare, pregătire transport.  
**12. Transport (Livrare)** – planificare traseu, încărcare, livrare.  
**13. Montaj** – instalare la client, reglaje, predare-recepție.
        """
    )

def render(ctx=None, **kwargs):
    st.markdown("## ❓ Ajutor & Ritmuri de lucru")

    tab1, tab2 = st.tabs(["Funcționalități aplicație", "Ritmuri pe secțiuni"])

    with tab1:
        _feature_list()

    with tab2:
        st.caption("Editează normele/ritmurile per secție. Persistă în `data/ritmuri.csv`.")
        df = _load_rates()

        # Filtru secție
        col1, col2 = st.columns([1,3])
        with col1:
            sec_sel = st.selectbox("Filtru secție", options=["(toate)"] + SECTIONS, index=0)
        v = df if sec_sel == "(toate)" else df[df["section"] == sec_sel].copy()
        edited = st.data_editor(
            v,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "section": st.column_config.SelectboxColumn("Secție", options=SECTIONS, width="medium"),
                "metric": st.column_config.TextColumn("Metrică", width="large"),
                "unit": st.column_config.TextColumn("Unitate", width="small"),
                "rate": st.column_config.NumberColumn("Ritm", step=0.1, width="small"),
                "note": st.column_config.TextColumn("Notă", width="large"),
            },
            key="rates_editor",
        )

        # Recompunem dataframe-ul complet dacă filtrat
        if sec_sel == "(toate)":
            new_df = edited
        else:
            new_df = df.copy()
            new_df.loc[new_df["section"] == sec_sel, :] = edited

        c1, c2, c3, c4 = st.columns([1,1,1,3])
        with c1:
            if st.button("💾 Salvează"):
                _save_rates(new_df)
                st.success("Ritmurile au fost salvate.")
        with c2:
            if st.button("↺ Resetează la recomandate"):
                _save_rates(pd.DataFrame(DEFAULT_RATES, columns=COLS))
                st.success("Resetat la setările recomandate.")
                st.rerun()
        with c3:
            buf = BytesIO()
            new_df.to_csv(buf, index=False)
            st.download_button("⬇️ Export CSV", data=buf.getvalue(), file_name="ritmuri_export.csv")
        with c4:
            up = st.file_uploader("Import CSV", type=["csv"], label_visibility="collapsed")
            if up is not None:
                try:
                    imp = pd.read_csv(up)
                    for c in COLS:
                        if c not in imp.columns:
                            imp[c] = "" if c != "rate" else 0.0
                    imp["rate"] = pd.to_numeric(imp["rate"], errors="coerce").fillna(0.0)
                    _save_rates(imp[COLS])
                    st.success("Import reușit.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Eroare la import: {e}")
