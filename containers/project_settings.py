\
from typing import Dict, Any
import streamlit as st
from datetime import date

def render(ctx: Dict[str, Any]):
    st.markdown("### ⚙️ Setări proiect (Contract)")
    st.info("Formular demo care ar transforma o ofertă într-un contract. Îl completăm după ce batem în cuie câmpurile.")

    with st.form("contract_form"):
        st.text_input("Denumire proiect")
        st.text_input("Număr contract (auto)")
        st.text_input("Client")
        st.text_input("Email client")
        st.text_input("Telefon client")
        st.text_input("Persoană contact montaj")
        st.text_input("Telefon persoană contact")
        st.text_input("Adresa livrare")

        c1, c2, c3 = st.columns(3)
        with c1: sign_date = st.date_input("Data contract", value=date.today())
        with c2: deadline  = st.date_input("Data livrare (contract)")
        with c3: ai_est    = st.date_input("Data estimată (AI)", value=date.today())

        st.checkbox("Transport la etaj (lift)")
        st.text_input("Link Google Maps / Waze")
        st.selectbox("Project Manager", options=ctx["data"].users["name"])
        st.number_input("Valoare contract (RON)", min_value=0.0, step=100.0)
        st.slider("Număr tranșe", 1, 4, 4)
        ok = st.form_submit_button("Salvează proiect")
    if ok:
        st.success("Proiect salvat (demo).")
