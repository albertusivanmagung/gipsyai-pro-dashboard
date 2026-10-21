# app.py - dashboard: login, filter global, 4 halaman
import streamlit as st
from auth import cek_login, tombol_logout
from filters import render_sidebar

st.set_page_config(page_title="GipsyAI Pro - Channel Akuisisi", layout="wide")

if not cek_login():
    st.navigation([st.Page("halaman/p1_overview.py")], position="hidden")
    st.stop()
render_sidebar()
tombol_logout()

halaman = st.navigation([
    st.Page("halaman/p1_overview.py", title="Overview dan Performa Channel",
            icon=":material/dashboard:", default=True),
    st.Page("halaman/p2_klaster.py", title="Hasil Klaster", icon=":material/hub:"),
    st.Page("halaman/p3_profil.py", title="Profil Segmen dan Channel", icon=":material/groups:"),
    st.Page("halaman/p4_detail.py", title="Detail Pelanggan", icon=":material/table:"),
])
halaman.run()