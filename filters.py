# filters.py - filter global dan fungsi bantu
import streamlit as st
from data import muat_pelanggan, muat_transaksi, sumber

WARNA_UTAMA = "#3987e5"
WARNA_SEGMEN = {  # urutan tampil sekaligus warna tetap tiap segmen
    "Pelanggan Setia Bernilai Tinggi": "#3987e5",
    "Pelanggan Baru Aktif": "#d95926",
    "Pelanggan Tidur": "#199e70",
    "Pelanggan Lama Nilai Rendah": "#c98500",
}


def fmt_int(x):
    return f"{int(x):,}".replace(",", ".")


def fmt_rp(x):
    return "Rp " + fmt_int(x)

def fmt_juta(x):
    teks = f"{x / 1_000_000:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"Rp {teks} juta"


def render_sidebar():
    """Menampilkan filter di sisi kiri (dipanggil sekali dari app.py)."""
    pel, trx = muat_pelanggan(), muat_transaksi()
    tmin, tmax = trx["tgl"].min().date(), trx["tgl"].max().date()
    channel = sorted(pel["channel_name"].unique())
    segmen = list(pel.groupby("segment_name")["customer_key"].count()
                  .sort_values(ascending=False).index)
    with st.sidebar:
        st.header("Filter")
        st.caption("Sumber data: " + ("snapshot CSV" if sumber() == "file" else "SQL Server"))
        st.date_input("Periode", value=(tmin, tmax), min_value=tmin,
                      max_value=tmax, key="f_periode")
        st.multiselect("Channel", channel, default=channel, key="f_channel")
        st.multiselect("Segmen", segmen, default=segmen, key="f_segmen")
        st.caption("Periode menyaring tanggal transaksi dan tanggal pembelian pertama "
                   "pelanggan. Segmen adalah hasil K-Means pada data seluruh periode.")


def data_terfilter():
    """Mengembalikan (pelanggan, transaksi) setelah filter diterapkan."""
    pel, trx = muat_pelanggan(), muat_transaksi()
    rentang = st.session_state.get("f_periode")
    if not rentang or len(rentang) != 2:
        st.info("Pilih tanggal akhir pada filter Periode.")
        st.stop()
    awal, akhir = rentang[0], rentang[1]
    ch = st.session_state.get("f_channel", [])
    sg = st.session_state.get("f_segmen", [])
    pel = pel[pel["tgl_akuisisi"].between(str(awal), str(akhir))
              & pel["channel_name"].isin(ch) & pel["segment_name"].isin(sg)]
    trx = trx[trx["tgl"].between(str(awal), str(akhir))
              & trx["channel_name"].isin(ch) & trx["segment_name"].isin(sg)]
    return pel, trx


def ringkasan():
    """Tiga angka uji (sementara) untuk memastikan filter bekerja."""
    pel, trx = data_terfilter()
    c1, c2, c3 = st.columns(3)
    c1.metric("Pelanggan", fmt_int(len(pel)))
    c2.metric("Transaksi berbayar", fmt_int(len(trx)))
    c3.metric("Pendapatan", fmt_rp(trx["amount"].sum()))