from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from data import muat_pelanggan, muat_transaksi
from db import baca
from filters import WARNA_SEGMEN, WARNA_UTAMA, data_terfilter, fmt_int

st.title("Hasil Klaster")
st.caption("Informasi model, grafik Elbow, dan Silhouette memakai seluruh data (tidak terpengaruh filter). "
           "Ukuran dan sebaran klaster mengikuti filter di sisi kiri.")

pel_semua = muat_pelanggan()
pel, _ = data_terfilter()
trx_semua = muat_transaksi()
URUT = list(WARNA_SEGMEN.keys())

# ---- data evaluasi K (dihasilkan KMeans.py) ----
csv_k = Path(__file__).resolve().parent.parent / "hasil" / "k_evaluasi.csv"
if not csv_k.exists():
    st.error(f"File {csv_k} tidak ditemukan. Jalankan KMeans.py terlebih dahulu.")
    st.stop()
evk = pd.read_csv(csv_k)
k_pilih = int(baca("SELECT MAX(k_value) AS k FROM dbo.Dim_Segment")["k"][0])
wcss = evk.loc[evk["K"] == k_pilih, "inertia"].iloc[0]
sil_total = pel_semua["silhouette_value"].mean()

# ---- angka model ----
m1, m2, m3, m4 = st.columns(4)
m1.metric("Jumlah klaster (K)", k_pilih)
m2.metric("Silhouette Score", f"{sil_total:.4f}".replace(".", ","))
m3.metric("WCSS (inertia)", fmt_int(wcss))
m4.metric("Pelanggan dimodelkan", fmt_int(len(pel_semua)))

awal, akhir = trx_semua["tgl"].min(), trx_semua["tgl"].max()
with st.expander("Informasi model", expanded=True):
    st.markdown(
        f"- **Algoritma:** K-Means Clustering, inisialisasi k-means++, 10 kali inisialisasi, random_state 42\n"
        f"- **Variabel:** Recency (hari), log(1+Frequency), log(1+Monetary), distandarkan dengan z-score\n"
        f"- **Data:** transaksi berbayar, {awal:%d-%m-%Y} sampai {akhir:%d-%m-%Y}; "
        f"tanggal acuan Recency 17-08-2026\n"
        f"- **Penentuan K:** Elbow Method dan Silhouette Score untuk K = 2 sampai 10"
    )

# ---- Elbow dan Silhouette per K ----
g1, g2 = st.columns(2)
fig_e = px.line(evk, x="K", y="inertia", markers=True,
                labels={"K": "Jumlah klaster (K)", "inertia": "WCSS (inertia)"})
fig_e.update_traces(line_color=WARNA_UTAMA, marker=dict(size=9, color=WARNA_UTAMA))
fig_e.add_vline(x=k_pilih, line_dash="dash", annotation_text=f"K = {k_pilih}")
fig_e.update_layout(title="Elbow Method", margin=dict(t=50, b=10))
fig_e.update_xaxes(dtick=1)
fig_e.update_yaxes(tickformat=",.0f")
g1.plotly_chart(fig_e, width="stretch")

fig_s = px.line(evk, x="K", y="silhouette", markers=True,
                labels={"K": "Jumlah klaster (K)", "silhouette": "Silhouette Score"})
fig_s.update_traces(line_color=WARNA_UTAMA, marker=dict(size=9, color=WARNA_UTAMA))
fig_s.add_vline(x=k_pilih, line_dash="dash", annotation_text=f"K = {k_pilih}")
fig_s.update_layout(title="Silhouette Score per K", margin=dict(t=50, b=10))
fig_s.update_xaxes(dtick=1)
g2.plotly_chart(fig_s, width="stretch")
g2.caption("K = 2 memberi skor tertinggi, tetapi hanya memisahkan pembeli satu kali dan pembeli "
           "berulang, terlalu kasar untuk analisis channel. K = 4 dipilih karena skornya tertinggi "
           "di antara K = 3 sampai 6, dan semua klasternya cukup besar.")

# ---- Ukuran klaster dan Silhouette per klaster ----
st.subheader("Ukuran klaster")
if pel.empty:
    st.warning("Tidak ada pelanggan untuk filter yang dipilih.")
    st.stop()

u1, u2 = st.columns([1, 1])
ukuran = (pel.groupby("segment_name").agg(pelanggan=("customer_key", "count"))
             .reindex(URUT).fillna(0).reset_index())
ukuran["persen"] = ukuran["pelanggan"] / ukuran["pelanggan"].sum() * 100
fig_u = px.bar(ukuran, x="segment_name", y="pelanggan", color="segment_name",
               color_discrete_map=WARNA_SEGMEN, category_orders={"segment_name": URUT},
               text=ukuran["persen"].map(lambda v: f"{v:.1f}%".replace(".", ",")),
               labels={"segment_name": "", "pelanggan": "Jumlah pelanggan"})
fig_u.update_traces(textposition="outside")
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
st.caption("Setiap titik adalah satu pelanggan. Sumbu Monetary memakai skala logaritma. "
           "Banyak titik berhimpit karena harga paket yang sama.")