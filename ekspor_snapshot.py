# ekspor_snapshot.py - ekspor data dashboard dari SQL Server ke CSV (untuk versi online)
import shutil
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
import pyodbc
from sqlalchemy import create_engine

SQL_SERVER = r"localhost\SQLEXPRESS"
SQL_DATABASE = "GipsyAI_Pro_DW"
KELUAR = Path("data_dashboard")
KELUAR.mkdir(exist_ok=True)


def pilih_driver():
    daftar = [d for d in pyodbc.drivers() if "SQL Server" in d]
    for d in ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server"):
        if d in daftar:
            return d
    raise RuntimeError("Driver ODBC SQL Server tidak ditemukan")


conn_str = (f"DRIVER={{{pilih_driver()}}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
            "Trusted_Connection=yes;TrustServerCertificate=yes")
eng = create_engine("mssql+pyodbc:///?odbc_connect=" + quote_plus(conn_str))

pelanggan = pd.read_sql("""
    WITH f AS (
        SELECT customer_key, MIN(transaction_datetime) AS first_paid
        FROM dbo.Fact_Transaction WHERE is_free = 0 GROUP BY customer_key
    )
    SELECT b.customer_key, c.customer_anon_id, ch.channel_name, s.segment_name,
           b.recency_days, b.frequency, b.monetary, b.silhouette_value,
           CAST(f.first_paid AS DATE) AS tgl_akuisisi
    FROM dbo.Fact_Customer_Behaviour b
    JOIN dbo.Dim_Customer c ON c.customer_key = b.customer_key
    JOIN dbo.Dim_Channel ch ON ch.channel_key = b.channel_key
    JOIN dbo.Dim_Segment s  ON s.segment_key  = b.segment_key
    JOIN f                  ON f.customer_key = b.customer_key
""", eng)

transaksi = pd.read_sql("""
    SELECT t.transaction_key, t.customer_key,
           CAST(t.transaction_datetime AS DATE) AS tgl,
           t.amount, ch.channel_name, s.segment_name
    FROM dbo.Fact_Transaction t
    JOIN dbo.Dim_Channel ch ON ch.channel_key = t.channel_key
    JOIN dbo.Fact_Customer_Behaviour b ON b.customer_key = t.customer_key
    JOIN dbo.Dim_Segment s ON s.segment_key = b.segment_key
    WHERE t.is_free = 0
""", eng)

segmen = pd.read_sql(
    "SELECT segment_name, segment_description, k_value FROM dbo.Dim_Segment", eng)

pelanggan.to_csv(KELUAR / "pelanggan.csv", index=False, encoding="utf-8")
transaksi.to_csv(KELUAR / "transaksi.csv", index=False, encoding="utf-8")
segmen.to_csv(KELUAR / "segmen.csv", index=False, encoding="utf-8")
shutil.copy(Path("hasil") / "k_evaluasi.csv", KELUAR / "k_evaluasi.csv")

print("pelanggan.csv   :", len(pelanggan), "baris | total monetary", int(pelanggan["monetary"].sum()))
print("transaksi.csv   :", len(transaksi), "baris | total amount  ", int(transaksi["amount"].sum()))
print("segmen.csv      :", len(segmen), "baris | K =", int(segmen["k_value"].max()))
print("k_evaluasi.csv  :", len(pd.read_csv(KELUAR / "k_evaluasi.csv")), "baris")
print("Kolom pelanggan :", list(pelanggan.columns))