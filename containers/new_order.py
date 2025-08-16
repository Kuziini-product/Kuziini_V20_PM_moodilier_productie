\
from typing import Dict, Any
import streamlit as st
from datetime import date

def render(ctx: Dict[str, Any]):
    st.markdown("### 📝 Comandă nouă / Ofertă")
    with st.form("offer_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            client = st.text_input("Client")
            email = st.text_input("Email client")
            phone = st.text_input("Telefon client")
            value = st.number_input("Valoare ofertă (RON)", min_value=0.0, step=100.0)
            offer_date = st.date_input("Data ofertei", value=date.today())
        with col2:
            contact_site = st.text_input("Persoană contact la locație")
            phone_site = st.text_input("Telefon contact")
            notes = st.text_area("Note")
        submitted = st.form_submit_button("Salvează ofertă")
    if submitted:
        st.session_state.setdefault("offers", []).append({
            "client": client, "email": email, "phone": phone, "value": value,
            "offer_date": str(offer_date), "contact_site": contact_site, "phone_site": phone_site, "notes": notes
        })
        st.success("Ofertă salvată.")
    st.divider()
    st.markdown("#### Oferte curente")
    st.write(st.session_state.get("offers", []))
