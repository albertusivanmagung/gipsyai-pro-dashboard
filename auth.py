# auth.py - login dan logout sederhana
import hmac

import streamlit as st


def _akun():
    try:
        return dict(st.secrets["users"])
    except Exception:
        return None


def cek_login():
    """True jika sudah login; jika belum, tampilkan form login."""
    if st.session_state.get("login_user"):
        return True
    akun = _akun()
    if akun is None:
        st.error("File .streamlit/secrets.toml belum dibuat atau tidak memuat bagian [users].")
        return False
    _, tengah, _ = st.columns([1, 1.2, 1])
    with tengah:
        st.title("GipsyAI Pro")
        st.caption("Dashboard Channel Akuisisi Pelanggan. Silakan masuk.")
        with st.form("form_login"):
            user = st.text_input("Username")
            pw = st.text_input("Password", type="password")
            kirim = st.form_submit_button("Masuk")
        if kirim:
            u = user.strip().lower()
            if u in akun and hmac.compare_digest(str(akun[u]).encode(), pw.encode()):
                st.session_state["login_user"] = u
                st.rerun()
            else:
                st.error("Username atau password salah.")
    return False


def tombol_logout():
    with st.sidebar:
        st.divider()
        st.write(f"Masuk sebagai **{st.session_state['login_user'].upper()}**")
        if st.button("Logout"):
            st.session_state.clear()
            st.rerun()