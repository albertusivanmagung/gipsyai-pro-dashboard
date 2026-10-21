# data.py - pengambilan data: SQL Server (lokal) atau CSV snapshot (online)
from pathlib import Path

import pandas as pd
import streamlit as st
from db import baca

FOLDER = Path(__file__).resolve().parent / "data_dashboard"


def sumber():
    try:
        return st.secrets.get("sumber_data", "sql")
    except Exception:
        return "sql"


@st.cache_data
def _csv(nama, kolom_tanggal=()):
    df = pd.read_csv(FOLDER / nama, dtype={"customer_anon_id": str})
    for k in kolom_tanggal:
        df[k] = pd.to_datetime(df[k])
    return df


def muat_pelanggan():
    """Satu baris per pelanggan berbayar (7.151 baris)."""
    if sumber() == "file":
        return _csv("pelanggan.csv", ("tgl_akuisisi",)).copy()
    df = baca("""
        WITH f AS (
            SELECT customer_key, MIN(transaction_datetime) AS first_paid
            FROM dbo.Fact_Transaction
            WHERE is_free = 0
            GROUP BY customer_key
        )
        SELECT b.customer_key, c.customer_anon_id, ch.channel_name, s.segment_name,
               b.recency_days, b.frequency, b.monetary, b.silhouette_value,
               CAST(f.first_paid AS DATE) AS tgl_akuisisi
        FROM dbo.Fact_Customer_Behaviour b
        JOIN dbo.Dim_Customer c  ON c.customer_key  = b.customer_key
        JOIN dbo.Dim_Channel ch  ON ch.channel_key  = b.channel_key
        JOIN dbo.Dim_Segment s   ON s.segment_key   = b.segment_key
        JOIN f                   ON f.customer_key  = b.customer_key
    """)
    df["tgl_akuisisi"] = pd.to_datetime(df["tgl_akuisisi"])
    return df


def muat_transaksi():
    """Satu baris per transaksi berbayar (8.153 baris)."""
    if sumber() == "file":
        return _csv("transaksi.csv", ("tgl",)).copy()
    df = baca("""
        SELECT t.transaction_key, t.customer_key,
               CAST(t.transaction_datetime AS DATE) AS tgl,
               t.amount, ch.channel_name, s.segment_name
        FROM dbo.Fact_Transaction t
        JOIN dbo.Dim_Channel ch ON ch.channel_key = t.channel_key
        JOIN dbo.Fact_Customer_Behaviour b ON b.customer_key = t.customer_key
        JOIN dbo.Dim_Segment s ON s.segment_key = b.segment_key
        WHERE t.is_free = 0
    """)
    df["tgl"] = pd.to_datetime(df["tgl"])
    return df


def muat_segmen():
    """4 segmen: nama, deskripsi, nilai K."""
    if sumber() == "file":
        return _csv("segmen.csv").copy()
    return baca("SELECT segment_name, segment_description, k_value FROM dbo.Dim_Segment")


def muat_k_evaluasi():
    """Hasil Elbow dan Silhouette untuk K = 2 sampai 10."""
    lokal = FOLDER.parent / "hasil" / "k_evaluasi.csv"
    if sumber() == "sql" and lokal.exists():
        return pd.read_csv(lokal)
    return _csv("k_evaluasi.csv").copy()