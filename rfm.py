#Langkah R1
# rfm.py  -  Langkah R1: baca transaksi berbayar dari data warehouse
import re, sys, urllib.parse
import pandas as pd
import pyodbc
from sqlalchemy import create_engine

SQL_SERVER   = r"localhost\SQLEXPRESS"
SQL_DATABASE = "GipsyAI_Pro_DW"

def pilih_driver():
    cocok = [d for d in pyodbc.drivers() if re.match(r"ODBC Driver \d+ for SQL Server", d)]
    if not cocok:
        sys.exit("Driver ODBC for SQL Server belum terpasang: " + str(pyodbc.drivers()))
    return max(cocok, key=lambda d: int(re.search(r"\d+", d).group()))

drv = pilih_driver()
odbc = (f"DRIVER={{{drv}}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
        f"Trusted_Connection=yes;TrustServerCertificate=yes;")
eng = create_engine("mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(odbc))

QUERY = """
SELECT f.transaction_key, f.customer_key, c.customer_anon_id,
       f.channel_key, ch.channel_name,
       f.transaction_datetime, f.amount
FROM dbo.Fact_Transaction f
JOIN dbo.Dim_Customer c ON c.customer_key = f.customer_key
JOIN dbo.Dim_Channel ch ON ch.channel_key = f.channel_key
WHERE f.is_free = 0
"""
trx = pd.read_sql(QUERY, eng)

print("Driver ODBC:", drv)
print("Transaksi berbayar dibaca:", f"{len(trx):,}")
print("Pelanggan unik:", f"{trx['customer_key'].nunique():,}")
print("Total amount: Rp", f"{int(trx['amount'].sum()):,}")
print("Transaksi pertama:", trx['transaction_datetime'].min())
print("Transaksi terakhir:", trx['transaction_datetime'].max())
print("Jumlah channel:", trx['channel_name'].nunique())
print("Ada amount nol?", bool((trx['amount'] == 0).any()))
print(trx.head(3).to_string())

#Langkah R2
# ---------- Langkah R2: hitung Recency, Frequency, Monetary per pelanggan ----------
import numpy as np

REF_DATE = pd.Timestamp("2026-08-17")        # satu hari setelah transaksi terakhir di data

trx = trx.sort_values(["customer_key", "transaction_datetime", "transaction_key"])
rfm = trx.groupby("customer_key").agg(
    customer_anon_id=("customer_anon_id", "first"),
    channel_key=("channel_key", "first"),
    channel_name=("channel_name", "first"),
    last_trx=("transaction_datetime", "max"),
    frequency=("transaction_key", "nunique"),
    monetary=("amount", "sum"),
).reset_index()
rfm["recency_days"] = (REF_DATE - rfm["last_trx"].dt.normalize()).dt.days

print("\n=== R2: RFM per pelanggan ===")
print("Jumlah pelanggan:", f"{len(rfm):,}")
print("Total monetary: Rp", f"{int(rfm['monetary'].sum()):,}")
print("Recency min / maks (hari):", rfm["recency_days"].min(), "/", rfm["recency_days"].max())
print("\nRingkasan R, F, M:")
print(rfm[["recency_days", "frequency", "monetary"]].describe().round(1).to_string())
print("\nSebaran Frequency:")
print(rfm["frequency"].value_counts().sort_index().to_string())
print("\nPelanggan dengan Frequency = 1:", f"{(rfm['frequency'] == 1).mean():.1%}")
print("\nPelanggan per channel:")
print(rfm["channel_name"].value_counts().to_string())
print("\nContoh 3 baris:")
print(rfm[["customer_key", "channel_name", "recency_days", "frequency", "monetary"]].head(3).to_string())

#Langkah R3

# ---------- Langkah R3: transformasi log dan pemeriksaan sebaran ----------
rfm["log_frequency"] = np.log1p(rfm["frequency"])     # ln(1 + F)
rfm["log_monetary"]  = np.log1p(rfm["monetary"])      # ln(1 + M)

print("\n=== R3: transformasi log ===")
kol_log = ["log_frequency", "log_monetary"]
print("Ada nilai kosong di kolom log?", bool(rfm[kol_log].isna().any().any()))
print("Ada nilai tak terhingga di kolom log?", bool(np.isinf(rfm[kol_log]).any().any()))

print("\nKemiringan sebaran (skewness; makin dekat 0 makin simetris):")
skew = pd.Series({
    "recency_days": rfm["recency_days"].skew(),
    "frequency": rfm["frequency"].skew(),
    "log_frequency": rfm["log_frequency"].skew(),
    "monetary": rfm["monetary"].skew(),
    "log_monetary": rfm["log_monetary"].skew(),
})
print(skew.round(2).to_string())

print("\nRingkasan kolom log:")
print(rfm[kol_log].describe().round(3).to_string())

print("\nContoh sebelum -> sesudah log:")
print(rfm[["customer_key", "frequency", "log_frequency", "monetary", "log_monetary"]].head(3).round(4).to_string())

#Langkah R4

# ---------- Langkah R4: tulis ke Fact_Customer_Behaviour ----------
from sqlalchemy import text

fcb = pd.DataFrame({
    "customer_key":     rfm["customer_key"].astype(int),
    "date_key":         int(REF_DATE.strftime("%Y%m%d")),     # 20260817 (tanggal acuan)
    "channel_key":      rfm["channel_key"].astype(int),
    "recency_days":     rfm["recency_days"].astype(int),
    "frequency":        rfm["frequency"].astype(int),
    "monetary":         rfm["monetary"].astype("int64"),
    "log_frequency":    rfm["log_frequency"].astype(float),
    "log_monetary":     rfm["log_monetary"].astype(float),
})

with eng.begin() as con:
    con.execute(text("DELETE FROM dbo.Fact_Customer_Behaviour"))      # kosongkan dulu (aman diulang)
    fcb.to_sql("Fact_Customer_Behaviour", con, schema="dbo",
               if_exists="append", index=False, chunksize=500)
    n, mon = con.execute(text(
        "SELECT COUNT(*), SUM(monetary) FROM dbo.Fact_Customer_Behaviour")).one()

print("\n=== R4: tulis ke SQL Server ===")
print(f"Tertulis di SQL Server: {n:,} baris, total monetary Rp {int(mon):,}")
assert n == len(rfm) and int(mon) == int(rfm["monetary"].sum()), "Jumlah di SQL Server tidak cocok dengan pandas!"
print("Verifikasi jumlah baris dan total monetary: COCOK")