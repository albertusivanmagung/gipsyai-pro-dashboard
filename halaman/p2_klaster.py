from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from data import muat_k_evaluasi, muat_pelanggan, muat_segmen, muat_transaksi
from filters import WARNA_SEGMEN, WARNA_UTAMA, data_terfilter, fmt_int

st.title("Hasil Klaster")

pel_semua = muat_pelanggan()
pel, _ = data_terfilter()
trx_semua = muat_transaksi()
URUT = list(WARNA_SEGMEN.keys())

# ---- data evaluasi K (dihasilkan KMeans.py) ----
evk = muat_k_evaluasi()
k_pilih = int(muat_segmen()["k_value"].max())
wcss = evk.loc[evk["K"] == k_pilih, "inertia"].iloc[0]
sil_total = pel_semua["silhouette_value"].mean()

# ---- angka model ----
m1, m2, m3, m4 = st.columns(4)
m1.metric("Jumlah klaster (K)", k_pilih,
          help="Jumlah kelompok pelanggan yang dibentuk model. Di sini pelanggan dibagi menjadi 4 kelompok (segmen).")
m2.metric("Silhouette Score", f"{sil_total:.4f}".replace(".", ","),
          help="Ukuran seberapa jelas pelanggan terpisah antar kelompok, dari −1 sampai 1. "
               "Makin dekat ke 1 makin jelas. Nilai sekitar 0 berarti kelompok saling tumpang tindih.")
m3.metric("WCSS (inertia)", fmt_int(wcss),
          help="Jumlah jarak kuadrat setiap pelanggan ke pusat kelompoknya. Makin kecil, anggota kelompok makin rapat. "
               "Dipakai untuk membandingkan jumlah K pada grafik Elbow.")
m4.metric("Pelanggan dimodelkan", fmt_int(len(pel_semua)),
          help="Jumlah pelanggan yang ikut dikelompokkan oleh model (seluruh data, tidak terpengaruh filter).")
awal, akhir = trx_semua["tgl"].min(), trx_semua["tgl"].max()

with st.expander("Informasi model", expanded=True):
    st.markdown(
        f"- **Algoritma:** K-Means Clustering, inisialisasi k-means++, 10 kali inisialisasi, random_state 42\n"
        f"- **Variabel:** Recency (hari), log(1+Frequency), log(1+Monetary), distandarkan dengan z-score\n"
        f"- **Data:** transaksi berbayar, {awal:%d-%m-%Y} sampai {akhir:%d-%m-%Y}; "
        f"tanggal acuan Recency 17-08-2026\n"
        f"- **Penentuan K:** Elbow Method dan Silhouette Score untuk K = 2 sampai 10"
    )
    st.markdown("**Apa itu K-Means?**")
    st.markdown(
        "K-Means adalah metode pengelompokan (*clustering*) yang membagi pelanggan ke dalam "
        "K kelompok berdasarkan kemiripan perilakunya (Recency, Frequency, Monetary). Caranya: "
        "(1) tentukan jumlah kelompok K, (2) tempatkan K titik pusat awal, (3) setiap pelanggan "
        "masuk ke pusat terdekat, (4) pusat dihitung ulang dari rata-rata anggotanya, "
        "(5) langkah 3 dan 4 diulang sampai kelompok tidak berubah lagi. Hasilnya, pelanggan "
        "dalam satu kelompok saling mirip dan berbeda dari kelompok lain."
    )

# ---- Toggle informasi halaman ----
with st.expander("Cara membaca halaman ini"):
    st.markdown(
        "- **Angka di bagian atas** (Jumlah klaster, Silhouette Score, WCSS, Pelanggan dimodelkan) "
        "menilai kualitas model. Arahkan kursor ke ikon (?) untuk penjelasan tiap angka.\n"
        "- **Elbow Method** dan **Silhouette Score per K** membantu memilih jumlah klaster. "
        "Keduanya memakai seluruh data, jadi tidak berubah saat filter diganti.\n"
        "- **Ukuran klaster** menunjukkan jumlah pelanggan tiap segmen, dan **Sebaran klaster** "
        "menunjukkan posisi setiap pelanggan. Keduanya mengikuti filter di sidebar.\n"
        "- **Pada Sebaran klaster**, satu titik adalah satu pelanggan. Sumbu Monetary memakai skala "
        "logaritma, dan titik yang berhimpit berasal dari harga paket yang sama."
    )

# ---- Elbow dan Silhouette per K ----
TIP_ELBOW = (
    "**Cara membaca:** WCSS (inertia) adalah jumlah jarak kuadrat setiap pelanggan ke pusat "
    "klasternya. Semakin kecil, anggota klaster semakin rapat.\n\n"
    "Nilai ini selalu turun saat K bertambah, jadi yang dicari adalah \"siku\", yaitu titik "
    "setelah itu penurunannya mulai melandai.\n\n"
    "Di sini penurunan mulai melandai sekitar K = 4, sehingga K = 4 dipilih sebagai titik "
    "tengah antara klaster yang rapat dan jumlah klaster yang tidak terlalu banyak."
)
TIP_SIL = (
    "**Cara membaca:** Silhouette mengukur seberapa cocok setiap pelanggan dengan klasternya "
    "dibanding klaster tetangga. Nilainya −1 sampai 1.\n\n"
    "- Mendekati 1: klaster rapat dan terpisah jelas.\n"
    "- Sekitar 0: klaster saling tumpang tindih.\n"
    "- Negatif: pelanggan kemungkinan salah klaster.\n\n"
    "Jadi semakin kecil nilainya, semakin kabur batas antar-klaster.\n\n"
    "K = 2 tertinggi, tetapi hanya menghasilkan 2 kelompok yang terlalu kasar. "
    "K = 4 dipilih karena menghasilkan 4 segmen yang bisa ditafsirkan."
)

g1, g2 = st.columns(2)
g1.subheader("Elbow Method", help=TIP_ELBOW)
fig_e = px.line(evk, x="K", y="inertia", markers=True,
                labels={"K": "Jumlah klaster (K)", "inertia": "WCSS (inertia)"})
fig_e.update_traces(line_color=WARNA_UTAMA, marker=dict(size=9, color=WARNA_UTAMA))
fig_e.add_vline(x=k_pilih, line_dash="dash", annotation_text=f"K = {k_pilih}")
fig_e.update_layout(margin=dict(t=10, b=10))
fig_e.update_xaxes(dtick=1)
fig_e.update_yaxes(tickformat=",.0f")
g1.plotly_chart(fig_e, width="stretch")

g2.subheader("Silhouette Score per K", help=TIP_SIL)
fig_s = px.line(evk, x="K", y="silhouette", markers=True,
                labels={"K": "Jumlah klaster (K)", "silhouette": "Silhouette Score"})
fig_s.update_traces(line_color=WARNA_UTAMA, marker=dict(size=9, color=WARNA_UTAMA))
fig_s.add_vline(x=k_pilih, line_dash="dash", annotation_text=f"K = {k_pilih}")
fig_s.update_layout(margin=dict(t=10, b=10))
fig_s.update_xaxes(dtick=1)
g2.plotly_chart(fig_s, width="stretch")

# ---- Ukuran klaster dan Silhouette per klaster ----
st.subheader("Ukuran klaster")
if pel.empty:
    st.warning("Tidak ada pelanggan untuk filter yang dipilih.")
    st.stop()

u1, u2 = st.columns([1, 1])
ukuran = (pel.groupby("segment_name").agg(pelanggan=("customer_key", "count"))
             .reindex(URUT).fillna(0).reset_index())
ukuran["persen"] = ukuran["pelanggan"] / ukuran["pelanggan"].sum() * 100
fig_u = px.bar(ukuran, x="pelanggan", y="segment_name", color="segment_name",
               orientation="h", color_discrete_map=WARNA_SEGMEN,
               category_orders={"segment_name": URUT},
               text=ukuran["persen"].map(lambda v: f"{v:.1f}%".replace(".", ",")),
               labels={"segment_name": "", "pelanggan": "Jumlah pelanggan"})
fig_u.update_traces(textposition="outside")
fig_u.update_yaxes(autorange="reversed")
fig_u.update_xaxes(range=[0, ukuran["pelanggan"].max() * 1.2])
fig_u.update_layout(showlegend=False, margin=dict(t=30, b=10))
u1.plotly_chart(fig_u, width="stretch")

sil_klaster = (pel_semua.groupby("segment_name")
               .agg(pelanggan=("customer_key", "count"), silhouette=("silhouette_value", "mean"))
               .reindex(URUT).reset_index())
u2.markdown("**Silhouette rata-rata per klaster** (seluruh data)")
u2.dataframe(sil_klaster, hide_index=True, width="stretch",
             column_config={"segment_name": "Segmen", "pelanggan": "Pelanggan",
                            "silhouette": st.column_config.NumberColumn("Silhouette", format="%.3f")})

# ---- Sebaran klaster ----
st.subheader("Sebaran klaster")
fig_sb = px.scatter(pel, x="recency_days", y="monetary", facet_col="segment_name",
                    facet_col_wrap=2, color="segment_name", color_discrete_map=WARNA_SEGMEN,
                    category_orders={"segment_name": URUT}, opacity=0.5, log_y=True,
                    hover_data=["customer_anon_id", "frequency"],
                    labels={"recency_days": "Recency (hari)", "monetary": "Monetary (Rp)"})
fig_sb.update_traces(marker=dict(size=6))
fig_sb.update_layout(showlegend=False, height=620)
fig_sb.update_yaxes(tickvals=[10000, 20000, 50000, 100000, 200000, 500000],
                    ticktext=["10rb", "20rb", "50rb", "100rb", "200rb", "500rb"])
fig_sb.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
st.plotly_chart(fig_sb, width="stretch")