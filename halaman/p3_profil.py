import pandas as pd
import plotly.express as px
import streamlit as st
from data import muat_segmen
from filters import WARNA_SEGMEN, data_terfilter, fmt_int, fmt_rp

st.title("Profil Segmen dan Channel")
pel, trx = data_terfilter()
if pel.empty:
    st.warning("Tidak ada pelanggan untuk filter yang dipilih.")
    st.stop()
URUT = list(WARNA_SEGMEN.keys())

# ---- 1. Profil segmen ----
st.subheader("Profil segmen")
rev = trx.groupby("segment_name")["amount"].sum().reindex(URUT).fillna(0)
prof = pel.groupby("segment_name").agg(
    pelanggan=("customer_key", "count"),
    recency=("recency_days", "mean"),
    frequency=("frequency", "mean"),
    monetary=("monetary", "mean"),
    repeat=("frequency", lambda s: (s > 1).mean() * 100),
).reindex(URUT).fillna(0)
prof["persen_pelanggan"] = prof["pelanggan"] / prof["pelanggan"].sum() * 100
prof["persen_pendapatan"] = rev / (rev.sum() or 1) * 100
tampil = prof.reset_index().assign(monetary=lambda d: d["monetary"].map(fmt_rp))
tampil = tampil[["segment_name", "pelanggan", "persen_pelanggan", "persen_pendapatan",
                 "recency", "frequency", "monetary", "repeat"]]
st.dataframe(
    tampil, hide_index=True, width="stretch",
    column_config={
        "segment_name": "Segmen",
        "pelanggan": "Pelanggan",
        "persen_pelanggan": st.column_config.NumberColumn("% pelanggan", format="%.1f%%"),
        "persen_pendapatan": st.column_config.NumberColumn("% pendapatan", format="%.1f%%"),
        "recency": st.column_config.NumberColumn("Recency rata-rata (hari)", format="%.1f"),
        "frequency": st.column_config.NumberColumn("Frequency rata-rata", format="%.2f"),
        "monetary": "Monetary rata-rata",
        "repeat": st.column_config.NumberColumn("% repeat", format="%.1f%%"),
    },
)
deskripsi = muat_segmen().set_index("segment_name")["segment_description"]
with st.expander("Deskripsi segmen"):
    for s in URUT:
        st.markdown(f"**{s}**: {deskripsi.get(s, '')}")

# ---- data silang channel x segmen ----
jum = pd.crosstab(pel["channel_name"], pel["segment_name"]).reindex(columns=URUT, fill_value=0)

# ---- 2. Komposisi channel dalam tiap segmen ----
st.subheader("Komposisi channel dalam tiap segmen")
st.caption("Setiap kolom berjumlah 100%: dari seluruh pelanggan satu segmen, berapa persen yang "
           "berasal dari tiap channel.")
komposisi = (jum / jum.sum().replace(0, 1) * 100)
komposisi = komposisi.loc[jum.sum(axis=1).sort_values(ascending=False).index]
komposisi.columns = [c.replace("Pelanggan ", "") for c in komposisi.columns]
fig_h = px.imshow(komposisi.round(1), text_auto=".1f", aspect="auto",
                  color_continuous_scale=["#16253b", "#3987e5"],
                  labels=dict(x="", y="", color="% dalam segmen"))
fig_h.update_xaxes(side="top", tickangle=0)
fig_h.update_layout(height=540, margin=dict(t=60, b=10))
st.plotly_chart(fig_h, width="stretch")

# ---- 3. Kualitas channel: komposisi segmen dalam tiap channel ----
st.subheader("Kualitas channel: komposisi segmen dalam tiap channel")
st.caption("Setiap batang berjumlah 100%: dari seluruh pelanggan satu channel, berapa persen yang "
           "masuk tiap segmen. Diurutkan dari porsi segmen Setia terbesar (paling atas).")
n_ch = jum.sum(axis=1)
label = {c: f"{c} (n={fmt_int(n_ch[c])})" for c in jum.index}
kual = (jum.div(n_ch, axis=0) * 100).fillna(0)
urut_q = list(kual[URUT[0]].sort_values(ascending=False).index)   # porsi Setia terbesar di paling atas
panjang = (kual.loc[urut_q].reset_index()
               .melt(id_vars="channel_name", var_name="segmen", value_name="persen"))
panjang["channel"] = panjang["channel_name"].map(label)
fig_q = px.bar(panjang, x="persen", y="channel", color="segmen", orientation="h",
               color_discrete_map=WARNA_SEGMEN,
               category_orders={"segmen": URUT, "channel": [label[c] for c in urut_q]},
               text=panjang["persen"].map(lambda v: f"{v:.0f}%" if v >= 5 else ""),
               labels={"persen": "% pelanggan channel", "channel": "", "segmen": "Segmen"})
fig_q.update_traces(marker_line_color="#0e1117", marker_line_width=2,
                    textfont_color="#0e1117", insidetextanchor="middle")
fig_q.update_layout(barmode="stack", height=600, margin=dict(t=110, b=10),
                    legend=dict(orientation="h", y=1.12, x=0))
fig_q.update_xaxes(range=[0, 100])
st.plotly_chart(fig_q, width="stretch")
st.caption("Porsi Baru Aktif dan Tidur dipengaruhi kapan sebuah channel mulai atau berhenti dipakai "
           "(lihat kolom akuisisi di halaman Overview), sehingga perbandingan kualitas channel "
           "terutama dibaca dari porsi segmen Setia. Channel dengan n kecil kurang dapat diandalkan.")