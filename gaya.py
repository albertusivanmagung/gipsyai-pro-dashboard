import streamlit as st

CSS = """
/* Latar halaman: gradasi mint sangat tipis */
.stApp {
    background: linear-gradient(180deg, #f3fbfa 0%, #e6f6f3 100%);
}

/* Judul halaman: gradasi biru tua ke teal */
.stApp h1 {
    background: linear-gradient(90deg, #183d60 0%, #118c89 60%, #09c9a8 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
    color: transparent;
}

/* Kartu KPI */
[data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.9);
    border: 1px solid #cdeae5;
    border-left: 6px solid #09c9a8;
    border-radius: 12px;
    padding: 6px 8px;
    box-shadow: 0 2px 8px rgba(24, 61, 96, 0.08);
}
[data-testid="stMetricValue"],
[data-testid="stMetricValue"] * {
    color: #183d60;
    font-size: 1.45rem !important;
}
[data-testid="stMetricLabel"],
[data-testid="stMetricLabel"] * {
    color: #155f72;
    font-size: 0.8rem !important;
}

/* Judul di sidebar harus terang */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h1 *,
[data-testid="stSidebar"] h2 *,
[data-testid="stSidebar"] h3 * {
    color: #e8f8f5 !important;
    -webkit-text-fill-color: #e8f8f5 !important;
}
"""


def terapkan_gaya():
    st.html(f"<style>{CSS}</style>")