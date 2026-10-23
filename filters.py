# filters.py - filter global dan fungsi bantu
import streamlit as st
from data import muat_pelanggan, muat_transaksi, sumber

WARNA_SEGMEN = {  # urutan tampil sekaligus warna tetap tiap segmen
    "Pelanggan Setia Bernilai Tinggi": "#3987e5",
    "Pelanggan Baru Aktif": "#d95926",
    "Pelanggan Tidur": "#199e70",
    "Pelanggan Lama Nilai Rendah": "#c98500",
}
# Palet dasar dashboard
PALET = ["#09c9a8", "#183d60", "#118c89", "#155f72", "#13757d",
         "#07d9b0", "#13a395", "#174d68", "#0bb79e"]
WARNA_UTAMA = "#118c89"      # warna utama grafik satu seri
WARNA_TEKS = "#183d60"       # teks dan judul

# Warna tiap channel (urutan mengikuti jumlah pelanggan, terbesar ke terkecil)
WARNA_CHANNEL = {
    "Instagram": "#183d60",              # palet: biru tua
    "Facebook": "#09c9a8",               # palet: teal terang
    "Instagram/Facebook": "#f08a4b",     # aksen: oranye
    "Website": "#7a5fc0",                # aksen: ungu
    "Google Search": "#118c89",          # palet: teal
    "Referral (Teman/Kerabat)": "#f4b942",  # aksen: kuning
    "Iklan": "#ef6f6c",                  # aksen: coral
    "TikTok": "#4da3e8",                 # aksen: biru langit
    "YouTube": "#d95f94",                # aksen: rose
    "Lainnya": "#8bc34a",                # aksen: hijau lime
    "Media Sosial (umum)": "#155f72",    # palet: biru kehijauan tua
    "Universitas/Institusi": "#5c6bc0",  # aksen: indigo
    "Email": "#07d9b0",                  # palet: mint
    "Tidak diketahui": "#9fb3b8",        # abu-abu (netral untuk data tak diketahui)
}


def warna_channel(nama):
    """Warna channel; abu-abu kalau namanya belum terdaftar."""
    return WARNA_CHANNEL.get(nama, "#9fb3b8")

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