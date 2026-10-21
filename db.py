# db.py - koneksi ke Data Warehouse (hanya dipakai pada mode "sql")
from urllib.parse import quote_plus

import pandas as pd
import streamlit as st

SQL_SERVER = r"localhost\SQLEXPRESS"
SQL_DATABASE = "GipsyAI_Pro_DW"


def _pilih_driver():
    import pyodbc  # hanya dibutuhkan pada mode SQL
    daftar = [d for d in pyodbc.drivers() if "SQL Server" in d]
    for d in ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server"):
        if d in daftar:
            return d
    raise RuntimeError("Driver ODBC SQL Server tidak ditemukan")


@st.cache_resource
def get_engine():
    from sqlalchemy import create_engine
    conn_str = (
        f"DRIVER={{{_pilih_driver()}}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
        "Trusted_Connection=yes;TrustServerCertificate=yes"
    )
    return create_engine("mssql+pyodbc:///?odbc_connect=" + quote_plus(conn_str))


@st.cache_data(ttl=600)
def baca(query: str) -> pd.DataFrame:
    return pd.read_sql(query, get_engine())