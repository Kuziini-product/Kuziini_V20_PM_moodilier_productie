from typing import Dict, Any
import streamlit as st

def render(ctx: Dict[str, Any]):
    st.markdown("### 👥 Utilizatori")
    st.dataframe(ctx["data"].users, use_container_width=True)
