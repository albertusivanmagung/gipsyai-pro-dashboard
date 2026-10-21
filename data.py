# data.py - pengambilan data dari Data Warehouse
import pandas as pd
from db import baca


def muat_pelanggan():
    """Satu baris per pelanggan berbayar (7.151 baris)."""
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