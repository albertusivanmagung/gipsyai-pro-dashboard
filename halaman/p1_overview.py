import plotly.express as px
import streamlit as st
from filters import data_terfilter, fmt_int, fmt_juta, fmt_rp

WARNA = "#4C78A8"
SETIA = "Pelanggan Setia Bernilai Tinggi"

st.title("Overview dan Performa Channel")
pel, trx = data_terfilter()
if pel.empty or trx.empty:
    st.warning("Tidak ada data untuk filter yang dipilih.")
    st.stop()

# ---- Angka ringkasan ----
k1, k2, k3, k4, k5 = st.columns([1.4, 1, 1.8, 1.6, 1.2])
k1.metric("Pelanggan baru", fmt_int(len(pel)),
          help="Pelanggan yang pembelian berbayar pertamanya terjadi dalam periode terpilih.")
k2.metric("Transaksi", fmt_int(len(trx)),
          help="Semua transaksi berbayar yang terjadi dalam periode, termasuk dari pelanggan lama.")
k3.metric("Pendapatan", fmt_juta(trx["amount"].sum()),
          help=f"Total nilai transaksi berbayar dalam periode: {fmt_rp(trx['amount'].sum())}")
k4.metric("Rata-rata transaksi", fmt_rp(trx["amount"].mean()))
repeat = (pel["frequency"] > 1).mean() * 100
k5.metric("Repeat", f"{repeat:.1f}%".replace(".", ","),
          help="Persentase pelanggan baru yang bertransaksi lebih dari satu kali.")

# ---- Grafik ----
g1, g2 = st.columns([3, 2])

bulanan = (trx.assign(bulan=trx["tgl"].dt.to_period("M").dt.to_timestamp())
              .groupby("bulan", as_index=False)
              .agg(pendapatan=("amount", "sum"), transaksi=("transaction_key", "count")))
fig1 = px.bar(bulanan, x="bulan", y="pendapatan", hover_data={"transaksi": True},
              color_discrete_sequence=[WARNA],
              labels={"bulan": "Bulan", "pendapatan": "Pendapatan (Rp)"})
fig1.update_layout(title="Pendapatan per bulan", margin=dict(t=50, b=10))
fig1.update_xaxes(tickformat="%b %Y")
fig1.update_yaxes(tickformat=",.0f")
g1.plotly_chart(fig1, width="stretch")
g1.caption("Juni 2025 (mulai 15 Juni) dan Agustus 2026 (sampai 16 Agustus) belum satu bulan penuh.")

per_ch = (pel.groupby("channel_name", as_index=False)
             .agg(pelanggan=("customer_key", "count"))
             .sort_values("pelanggan"))
fig2 = px.bar(per_ch, x="pelanggan", y="channel_name", orientation="h",
              color_discrete_sequence=[WARNA],
              labels={"pelanggan": "Jumlah pelanggan", "channel_name": ""})
fig2.update_layout(title="Pelanggan per channel", margin=dict(t=50, b=10))
g2.plotly_chart(fig2, width="stretch")

# ---- Tabel performa channel ----
st.subheader("Performa channel")
perf = pel.groupby("channel_name").agg(
    pelanggan=("customer_key", "count"),
    repeat=("frequency", lambda s: (s > 1).mean() * 100),
    setia=("segment_name", lambda s: (s == SETIA).mean() * 100),
    rata_belanja=("monetary", "mean"),
    awal=("tgl_akuisisi", "min"),
    akhir=("tgl_akuisisi", "max"),
)
rev = trx.groupby("channel_name").agg(transaksi=("transaction_key", "count"),
                                      pendapatan=("amount", "sum"))
perf = perf.join(rev, how="left").fillna(0).sort_values("pelanggan", ascending=False)
perf = perf.reset_index()

tabel = perf.assign(
    pendapatan=perf["pendapatan"].map(fmt_rp),
    rata_belanja=perf["rata_belanja"].map(fmt_rp),
    awal=perf["awal"].dt.strftime("%d-%m-%Y"),
    akhir=perf["akhir"].dt.strftime("%d-%m-%Y"),
)[["channel_name", "pelanggan", "transaksi", "pendapatan", "rata_belanja",
   "repeat", "setia", "awal", "akhir"]]
st.dataframe(
    tabel, hide_index=True, width="stretch",
    column_config={
        "channel_name": "Channel",
                "pelanggan": "Pelanggan baru",
        "transaksi": "Transaksi dalam periode",
        "pendapatan": "Pendapatan dalam periode",
        "rata_belanja": "Rata-rata belanja per pelanggan",
        "repeat": st.column_config.NumberColumn("% repeat", format="%.1f%%"),
        "setia": st.column_config.NumberColumn("% segmen Setia", format="%.1f%%"),
        "awal": "Akuisisi pertama",
        "akhir": "Akuisisi terakhir",
    },
)
st.caption(
    "ROAS tidak dapat dihitung karena data biaya iklan tidak tersedia pada penelitian ini. "
    "Tabel ini memberi dasar pertimbangan alokasi anggaran lewat kualitas pelanggan per channel "
    "(porsi pelanggan repeat dan segmen Setia). Channel dengan pelanggan sangat sedikit "
    "(misalnya Email dan Tidak diketahui) persentasenya kurang dapat diandalkan. "
    "Pelanggan baru adalah pelanggan yang pembelian pertamanya terjadi dalam periode; "
    "transaksi dan pendapatan mencakup semua pembelian dalam periode, termasuk dari pelanggan lama. "
    "Kolom akuisisi pertama dan terakhir menunjukkan kapan opsi channel dipakai."
)