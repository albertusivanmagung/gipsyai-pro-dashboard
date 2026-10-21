#Langkah K1
# KMeans.py - Tahap K-Means
import pyodbc
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sklearn.preprocessing import StandardScaler

SQL_SERVER = r"localhost\SQLEXPRESS"
SQL_DATABASE = "GipsyAI_Pro_DW"

def pilih_driver():
    daftar = [d for d in pyodbc.drivers() if "SQL Server" in d]
    for d in ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server"):
        if d in daftar:
            return d
    raise RuntimeError("Driver ODBC SQL Server tidak ditemukan")

driver = pilih_driver()
print("Driver:", driver)
conn_str = (
    f"DRIVER={{{driver}}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
    "Trusted_Connection=yes;TrustServerCertificate=yes"
)
eng = create_engine("mssql+pyodbc:///?odbc_connect=" + conn_str.replace(";", "%3B").replace(" ", "%20").replace("=", "%3D").replace("\\", "%5C").replace("{", "%7B").replace("}", "%7D"))

# ---- K1a: baca data ----
df = pd.read_sql("""
    SELECT customer_key, recency_days, frequency, monetary,
           log_frequency, log_monetary
    FROM dbo.Fact_Customer_Behaviour
    ORDER BY customer_key
""", eng)
print("\n[K1a] Jumlah baris :", len(df))
print("[K1a] Nilai kosong  :", int(df.isna().sum().sum()))

# ---- K1b: standarisasi z-score ----
FITUR = ["recency_days", "log_frequency", "log_monetary"]
X = StandardScaler().fit_transform(df[FITUR])
print("\n[K1b] Bentuk X      :", X.shape)
print("[K1b] Rata-rata     :", np.round(X.mean(axis=0), 6))
print("[K1b] Simpangan baku:", np.round(X.std(axis=0), 6))

#Langkah K2
# ---- K2: coba K = 2..10 (Elbow + Silhouette) ----
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, silhouette_samples

HASIL = "hasil"
os.makedirs(HASIL, exist_ok=True)

baris = []
for k in range(2, 11):
    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
    baris.append({
        "K": k,
        "inertia": round(km.inertia_, 1),
        "silhouette": round(silhouette_score(X, km.labels_), 4),
    })
hasil_k = pd.DataFrame(baris)
print("\n[K2] Perbandingan K")
print(hasil_k.to_string(index=False))
hasil_k.to_csv(os.path.join(HASIL, "k_evaluasi.csv"), index=False)

fig, ax = plt.subplots(1, 2, figsize=(11, 4))
ax[0].plot(hasil_k["K"], hasil_k["inertia"], marker="o")
ax[0].set_title("Elbow Method (Inertia/WCSS)")
ax[1].plot(hasil_k["K"], hasil_k["silhouette"], marker="o", color="green")
ax[1].set_title("Silhouette Score (makin tinggi makin baik)")
for a in ax:
    a.set_xlabel("Jumlah klaster (K)")
    a.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(HASIL, "k_evaluasi.png"), dpi=150)
print("Grafik disimpan: hasil\\k_evaluasi.png")

#Langkah K3
# ---- K3: kestabilan (Silhouette di 10 seed) + ukuran klaster ----
print("\n[K3] Kestabilan Silhouette (10 seed), ukuran, dan Silhouette per klaster")
for k in [3, 4, 5, 6]:
    sil = []
    for seed in range(1, 11):
        lab = KMeans(n_clusters=k, n_init=10, random_state=seed).fit(X).labels_
        sil.append(silhouette_score(X, lab))
    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
    s_i = silhouette_samples(X, km.labels_)
    ukuran = np.bincount(km.labels_)
    per_klaster = [round(s_i[km.labels_ == c].mean(), 3) for c in range(k)]
    print(f"K={k} | Silhouette 10 seed: rata-rata={np.mean(sil):.4f}  "
          f"min={np.min(sil):.4f}  maks={np.max(sil):.4f}")
    print(f"      ukuran klaster : {ukuran.tolist()}  "
          f"({np.round(ukuran / len(X) * 100, 1).tolist()} %)")
    print(f"      Silhouette per klaster: {per_klaster}")

#Langkah K4
# ---- K4: model akhir K=4 + profil klaster ----
K_FINAL = 4
km_final = KMeans(n_clusters=K_FINAL, n_init=10, random_state=42).fit(X)
df["cluster_id"] = km_final.labels_
df["silhouette_value"] = silhouette_samples(X, km_final.labels_)
print(f"\n[K4] Silhouette Score K={K_FINAL}: {silhouette_score(X, km_final.labels_):.4f}")

profil = df.groupby("cluster_id").agg(
    pelanggan=("customer_key", "count"),
    recency_rata2=("recency_days", "mean"),
    frequency_rata2=("frequency", "mean"),
    monetary_rata2=("monetary", "mean"),
    monetary_median=("monetary", "median"),
    total_monetary=("monetary", "sum"),
    silhouette=("silhouette_value", "mean"),
).round(2)
profil["persen_pelanggan"] = (profil["pelanggan"] / len(df) * 100).round(1)
profil["persen_pendapatan"] = (profil["total_monetary"] / df["monetary"].sum() * 100).round(1)
profil["persen_repeat(F>1)"] = (
    df.assign(repeat=df["frequency"] > 1).groupby("cluster_id")["repeat"].mean() * 100
).round(1)
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 20)
print(profil.T)
profil.to_csv(os.path.join(HASIL, "profil_klaster.csv"))    

#Langkah K5
# ---- K5a: nama segmen (berdasarkan aturan profil) ----
sid_setia = profil["frequency_rata2"].idxmax()
sisa = profil.drop(sid_setia)
sid_rendah = sisa["monetary_rata2"].idxmin()
sisa2 = sisa.drop(sid_rendah)
sid_baru = sisa2["recency_rata2"].idxmin()
sid_tidur = sisa2["recency_rata2"].idxmax()

nama_segmen = {
    sid_setia:  "Pelanggan Setia Bernilai Tinggi",
    sid_baru:   "Pelanggan Baru Aktif",
    sid_tidur:  "Pelanggan Tidur",
    sid_rendah: "Pelanggan Lama Nilai Rendah",
}
deskripsi_segmen = {
    "Pelanggan Setia Bernilai Tinggi": "Membeli berulang dengan total belanja tertinggi; kontribusi pendapatan terbesar per pelanggan.",
    "Pelanggan Baru Aktif": "Baru membeli satu kali dan transaksinya masih relatif baru; peluang untuk mendorong pembelian kedua.",
    "Pelanggan Tidur": "Membeli satu kali dan sudah lama tidak bertransaksi; perlu diaktifkan kembali.",
    "Pelanggan Lama Nilai Rendah": "Membeli satu kali, paling lama tidak aktif, dengan nilai belanja paling kecil.",
}
df["segment_name"] = df["cluster_id"].map(nama_segmen)

ringkas = profil[["pelanggan", "persen_pelanggan", "persen_pendapatan"]].copy()
ringkas.insert(0, "segment_name", ringkas.index.map(nama_segmen))
print("\n[K5a] Nama segmen")
print(ringkas.to_string())

# ---- K5b: komposisi channel di tiap segmen (persentase dalam segmen) ----
ch = pd.read_sql("""
    SELECT b.customer_key, c.channel_name
    FROM dbo.Fact_Customer_Behaviour b
    JOIN dbo.Dim_Channel c ON c.channel_key = b.channel_key
""", eng)
m = df.merge(ch, on="customer_key", how="left")
jumlah = pd.crosstab(m["channel_name"], m["segment_name"])
komposisi = (jumlah / jumlah.sum() * 100).round(1)
komposisi = komposisi.loc[jumlah.sum(axis=1).sort_values(ascending=False).index]
print("\n[K5b] Komposisi channel dalam tiap segmen (%, tiap kolom = 100)")
print(komposisi.to_string())
print("Total kolom:", komposisi.sum().round(1).to_dict())
print("Total pelanggan:", int(jumlah.values.sum()))

df.to_csv(os.path.join(HASIL, "segmen_pelanggan.csv"), index=False)
komposisi.to_csv(os.path.join(HASIL, "komposisi_channel_segmen.csv"))

#Langkah K6
# ---- K6: tulis hasil K-Means ke SQL Server ----
from sqlalchemy import text
from datetime import date

with eng.begin() as con:
    # kosongkan hasil lama
    con.execute(text("UPDATE dbo.Fact_Customer_Behaviour SET segment_key = NULL, silhouette_value = NULL"))
    con.execute(text("DELETE FROM dbo.Dim_Segment"))
    con.execute(text("DBCC CHECKIDENT ('dbo.Dim_Segment', RESEED, 0)"))

    # isi Dim_Segment
    for cid in sorted(nama_segmen):
        nama = nama_segmen[cid]
        con.execute(text(
            "INSERT INTO dbo.Dim_Segment (cluster_id, segment_name, segment_description, k_value, run_date) "
            "VALUES (:c, :n, :d, :k, :r)"),
            {"c": int(cid), "n": nama, "d": deskripsi_segmen[nama],
             "k": K_FINAL, "r": date.today()})

    # petakan cluster_id -> segment_key, lalu update fakta
    peta = pd.read_sql(text("SELECT segment_key, cluster_id FROM dbo.Dim_Segment"), con)
    upd = (df[["customer_key", "cluster_id", "silhouette_value"]]
           .merge(peta, on="cluster_id")[["customer_key", "segment_key", "silhouette_value"]])
    upd.to_sql("tmp_segmen_update", con, schema="dbo", if_exists="replace",
               index=False, chunksize=500)
    con.execute(text("""
        UPDATE b SET b.segment_key = u.segment_key, b.silhouette_value = u.silhouette_value
        FROM dbo.Fact_Customer_Behaviour b
        JOIN dbo.tmp_segmen_update u ON u.customer_key = b.customer_key
    """))
    con.execute(text("DROP TABLE dbo.tmp_segmen_update"))

# cek hasil dari sisi SQL
cek = pd.read_sql("""
    SELECT s.segment_key, s.cluster_id, s.segment_name, s.k_value,
           COUNT(*) AS pelanggan, ROUND(AVG(b.silhouette_value), 3) AS silhouette_rata2
    FROM dbo.Fact_Customer_Behaviour b
    JOIN dbo.Dim_Segment s ON s.segment_key = b.segment_key
    GROUP BY s.segment_key, s.cluster_id, s.segment_name, s.k_value
    ORDER BY s.segment_key
""", eng)
print("\n[K6] Hasil di SQL Server")
print(cek.to_string(index=False))
kosong = pd.read_sql("SELECT COUNT(*) AS n FROM dbo.Fact_Customer_Behaviour WHERE segment_key IS NULL", eng)["n"][0]
print("Pelanggan tanpa segmen:", kosong, "| Total:", int(cek["pelanggan"].sum()))