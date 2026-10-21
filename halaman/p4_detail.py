import streamlit as st
from filters import data_terfilter, fmt_int, fmt_rp

st.title("Detail Pelanggan")
pel, _ = data_terfilter()

cari = st.text_input("Cari ID anonim pelanggan",
                     placeholder="Ketik sebagian ID, lalu tekan Enter")
tabel = pel
if cari.strip():
    tabel = tabel[tabel["customer_anon_id"].str.contains(
        cari.strip(), case=False, regex=False, na=False)]
tabel = tabel.sort_values("monetary", ascending=False)

c1, c2, c3 = st.columns(3)
c1.metric("Pelanggan ditampilkan", fmt_int(len(tabel)))
c2.metric("Pelanggan sesuai filter", fmt_int(len(pel)))
c3.metric("Total monetary", fmt_rp(tabel["monetary"].sum()))

tampil = tabel[["customer_anon_id", "channel_name", "segment_name", "tgl_akuisisi",
                "recency_days", "frequency", "monetary"]].copy()
tampil["tgl_akuisisi"] = tampil["tgl_akuisisi"].dt.date

st.dataframe(
    tampil, hide_index=True, width="stretch", height=520,
    column_config={
        "customer_anon_id": "ID anonim",
        "channel_name": "Channel transaksi pertama",
        "segment_name": "Segmen",
        "tgl_akuisisi": st.column_config.DateColumn("Pembelian pertama", format="DD-MM-YYYY"),
        "recency_days": st.column_config.NumberColumn("Recency (hari)", format="%d"),
        "frequency": st.column_config.NumberColumn("Frequency", format="%d"),
        "monetary": st.column_config.NumberColumn("Monetary (Rp)", format="%d"),
    },
)

csv = (tampil.rename(columns={
            "customer_anon_id": "ID anonim", "channel_name": "Channel transaksi pertama",
            "segment_name": "Segmen", "tgl_akuisisi": "Pembelian pertama",
            "recency_days": "Recency (hari)", "frequency": "Frequency",
            "monetary": "Monetary (Rp)"})
       .to_csv(index=False).encode("utf-8-sig"))
st.download_button("Unduh CSV", csv, file_name="detail_pelanggan.csv",
                   mime="text/csv", disabled=tampil.empty)
st.caption("Nama, email, dan nomor HP pelanggan tidak ditampilkan dan tidak ikut diunduh. "
           "Data yang diunduh sesuai filter dan pencarian yang sedang aktif.")