import os, re, sys, html, hashlib, urllib.parse
import numpy as np
import pandas as pd

# =====================================================================
# KONFIGURASI  (ubah bagian ini saja)
# =====================================================================
# Folder proyek = folder tempat file ini disimpan (E:\Skripsi\GipsyAI Pro Skripsi). Tidak perlu mengetik path panjang.
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
SRC_FILE   = os.path.join(BASE_DIR, "data", "Customer - GipsyAI Pro - Super App untuk Penelitian.xlsx")
SHEET      = "Sheet1"
OUT_DIR    = os.path.join(BASE_DIR, "hasil")        # dibuat otomatis

# --- SQL Server (Windows Authentication), sesuai SSMS: Server name localhost\sqlexpress
SQL_SERVER   = r"localhost\SQLEXPRESS"
SQL_DATABASE = "GipsyAI_Pro_DW"
SQL_DRIVER   = None          # None = pilih otomatis driver "ODBC Driver xx for SQL Server" terbaru yang terpasang
STG_TABLE    = "stg_transaksi"
LOAD_TO_SQL  = True         # False = hanya cleaning + simpan CSV. Ubah ke True setelah hasilnya dicek

# --- Pilihan penelitian (bahas dengan dosen, lalu tulis keputusannya di Bab 3)
PERBAIKI_BARIS_BERGESER = True   # True  = 155 baris export lama diselamatkan (disarankan)
BUANG_TRANSAKSI_GRATIS  = False  # True  = transaksi Rp 0 (metode 'Gratis') tidak ikut staging
SALT = "albert-skripsi-gipsyai-2026"   # WAJIB diganti dengan kata rahasia Anda sendiri; simpan, jangan dibagikan

# --- Penanda (flag) data meragukan. Default: DITANDAI saja, tidak dibuang. Putuskan bersama mitra/dosen.
BUANG_DUPLIKAT_SUSPECT = False   # True = buang transaksi dengan email + jam yang persis sama (ID transaksi beda)
BUANG_AKUN_INTERNAL    = False   # True = buang akun uji coba / kupon internal
INTERNAL_COUPONS = {"INTERNGIPSYASIK", "GRA5GIPSYAI", "FREELANCE2026"}   # DUGAAN, konfirmasi ke mitra
INTERNAL_EMAIL_REGEX = r"^test\.test@test\.com$|^gipsync22@gmail\.com$"       # DUGAAN, konfirmasi ke mitra

# URL koneksi bisa ditimpa lewat variabel lingkungan STG_URL (dipakai untuk uji coba).
CH_COL = "Dari mana anda mengetahui Gipsy Research?"

if SALT.startswith("ganti-dengan") and LOAD_TO_SQL:
    sys.exit("Ganti dulu SALT di bagian KONFIGURASI dengan kata rahasia Anda sendiri.")
if SALT.startswith("ganti-dengan"):
    print("PERINGATAN: SALT belum diganti. Ganti sebelum memuat ke SQL Server.\n")
os.makedirs(OUT_DIR, exist_ok=True)
LOG = []                                  # catatan jumlah baris tiap langkah
def catat(langkah, df, ket=""):
    LOG.append({"langkah": langkah, "baris": len(df), "keterangan": ket})
    print(f"{langkah:<58}{len(df):>8,}  {ket}")

# =====================================================================
# 1. BACA DATA MENTAH
# =====================================================================
raw = pd.read_excel(SRC_FILE, sheet_name=SHEET, dtype=object)   # dtype=object: jangan ditebak dulu
catat("1. Data mentah", raw, f"{raw.shape[1]} kolom")
df = raw.copy()

# =====================================================================
# 2. RAPIKAN NAMA KOLOM  (nama asli -> nama baku tanpa spasi/simbol)
# =====================================================================
RENAME = {
    "Unnamed: 0": "row_uuid",
    "Amount": "amount_raw",
    "Admin Fee (Paid by Customer)": "admin_fee_raw",
    "Channel Fee (Paid by Customer)": "channel_fee_raw",
    "Customer Name": "customer_name",              # akan dibuang (data pribadi)
    "Customer Email": "customer_email",
    "Customer Mobile": "customer_mobile",          # akan dibuang (data pribadi)
    "Transaction Created At": "transaction_datetime",
    "Pixel Fbp": "pixel_fbp", "Pixel Fbc": "pixel_fbc",   # akan dibuang (pelacak iklan)
    "Institusi/Universitas": "institution_old",
    "Jurusan/ Program Studi/ Pekerjaan": "study_old",
    "Tujuan Penggunaan.1": "usage_purpose2",       # hanya ada di export terbaru
    CH_COL: "channel_raw",
    "Nama Produk": "product_name",
    "Tipe Produk": "product_type",
    "Transaction ID": "transaction_id",
    "Status": "status",
    "Metode Pembayaran": "payment_method",
    "Kode Kupon": "coupon_code",
    "Institusi/Universitas/Perusahaan": "institution_new",
    "Varian Produk": "product_variant",
    "Qty": "qty_raw",                              # akan dibuang (kolom tercampur teks)
    "Profesi": "profession",
    "Program Studi/ Bidang Pekerjaan": "study_new",
    "Tujuan Penggunaan": "usage_purpose",
}
df = df.rename(columns=RENAME)
if "usage_purpose2" not in df.columns:            # export lama tidak punya kolom ini
    df["usage_purpose2"] = np.nan
assert set(RENAME.values()) <= set(df.columns), "Ada kolom yang namanya tidak cocok dengan RENAME"

def bersih_teks(s):
    """strip, rapikan spasi ganda, ubah entitas HTML (&amp; -> &), '-' / kosong -> NaN"""
    s = s.astype("string").str.strip()
    s = s.map(lambda x: html.unescape(x) if pd.notna(x) else x)
    s = s.str.replace(r"\s+", " ", regex=True)
    return s.mask(s.isin(["-", "", "nan", "NaN", "None"]))

# --- pemeriksaan sementara langkah 2 (boleh dihapus nanti) ---
print("\nJumlah kolom setelah diberi nama baru:", df.shape[1])
print(df.columns.tolist())

# =====================================================================
# 3. PERBAIKI BARIS YANG KOLOMNYA BERGESER
#    Export lama (Jun-Jul 2025) urutannya: Status, Metode, Kupon, Transaction ID, sehingga
#    "Paid" tercatat di kolom Transaction ID, metode bayar di kolom Status, kupon di kolom
#    Metode Pembayaran, dan ID transaksi yang asli (UUID) di kolom Kode Kupon.
#    Baris ini TRANSAKSI SAH. 101 dari 155 baris punya UUID; 54 sisanya diberi ID LEGACY-xxxx.
# =====================================================================
geser = df["transaction_id"].astype("string").str.strip().str.lower().eq("paid")
df["is_realigned"] = False
if PERBAIKI_BARIS_BERGESER:
    old_status, old_metode = df.loc[geser, "status"].copy(), df.loc[geser, "payment_method"].copy()
    old_kupon = df.loc[geser, "coupon_code"].astype("string").str.strip()          # berisi ID transaksi asli (UUID)
    uuid_ok = old_kupon.str.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", case=False, na=False)
    df.loc[geser, "status"]         = "Paid"
    df.loc[geser, "payment_method"] = old_status      # metode bayar ada di kolom Status
    df.loc[geser, "coupon_code"]    = old_metode      # kupon ada di kolom Metode Pembayaran
    ids = [(u if ok else "LEGACY-%04d" % (i + 1)) for i, (u, ok) in enumerate(zip(old_kupon, uuid_ok))]
    df.loc[geser, "transaction_id"] = ids
    df.loc[geser, "is_realigned"]   = True
    catat("3. Baris bergeser diperbaiki", df, f"{int(geser.sum())} baris; ID asli dipulihkan {int(uuid_ok.sum())}, ID LEGACY-xxxx {int((~uuid_ok).sum())}")
else:
    catat("3. Baris bergeser TIDAK diperbaiki", df, f"{int(geser.sum())} baris akan terbuang di langkah 5")

# --- pemeriksaan sementara langkah 3 (boleh dihapus nanti) ---
bar = df[df["is_realigned"]]
print("\nBaris yang diperbaiki:", len(bar))
print("Contoh 3 baris sesudah diperbaiki:")
print(bar[["transaction_id", "status", "payment_method", "coupon_code", "amount_raw"]].head(3).to_string())
print("Masih ada transaction_id = 'Paid'?", (df["transaction_id"].astype("string").str.lower() == "paid").any())

# =====================================================================
# 4. BUANG BARIS TANPA INFORMASI TRANSAKSI
#    (20 baris awal, Mei-Jun 2025: Status, Produk, ID semuanya kosong)
# =====================================================================
kosong = df["status"].isna() & df["transaction_id"].isna() & df["product_name"].isna()
df = df[~kosong].copy()
catat("4. Buang baris tanpa data transaksi", df, f"{int(kosong.sum())} baris dibuang")

# =====================================================================
# 5. STATUS = PAID SAJA, BUANG DUPLIKAT
# =====================================================================
df["status"] = df["status"].astype("string").str.strip().str.title()
n0 = len(df); df = df[df["status"] == "Paid"].copy()
catat("5a. Hanya Status = Paid", df, f"{n0-len(df)} baris dibuang")

df["transaction_id"] = df["transaction_id"].astype("string").str.strip()
n0 = len(df); df = df.drop_duplicates("transaction_id", keep="first").copy()
catat("5b. Hapus duplikat Transaction ID", df, f"{n0-len(df)} baris dibuang")

# --- pemeriksaan sementara langkah 4 (boleh dihapus nanti) ---
print("\nStatus sekarang:", df["status"].value_counts().to_dict())
print("Transaction ID unik semua?", df["transaction_id"].is_unique)
print("Periode:", pd.to_datetime(df["transaction_datetime"]).min(), "s.d.", pd.to_datetime(df["transaction_datetime"]).max())

# =====================================================================
# 6. AMOUNT & FEE -> ANGKA
#    "Rp 29.904" -> 29904.   Admin/Channel fee berisi 'True' / '-' (penanda, bukan nominal).
# =====================================================================
df["amount"] = pd.to_numeric(
    df["amount_raw"].astype("string").str.replace(r"[^0-9]", "", regex=True), errors="coerce")
n0 = len(df); df = df[df["amount"].notna()].copy()
catat("6a. Amount valid (angka)", df, f"{n0-len(df)} baris dibuang")

def ke_bit(s):
    t = s.astype("string").str.strip().str.lower()
    return t.map({"true": 1, "-": 0, "false": 0}).astype("Int64")   # nilai lain (mis. nomor nyasar) -> NULL
df["admin_fee_flag"]   = ke_bit(df["admin_fee_raw"])
df["channel_fee_flag"] = ke_bit(df["channel_fee_raw"])
df["amount"] = df["amount"].astype("int64")
df["is_free"] = (df["amount"] == 0).astype(int)                  # transaksi gratis (metode 'Gratis')

if BUANG_TRANSAKSI_GRATIS:
    n0 = len(df); df = df[df["amount"] > 0].copy()
    catat("6b. Buang transaksi Rp 0", df, f"{n0-len(df)} baris dibuang")

# =====================================================================
# 7. TANGGAL
# =====================================================================
df["transaction_datetime"] = pd.to_datetime(df["transaction_datetime"], errors="coerce")
n0 = len(df); df = df[df["transaction_datetime"].notna()].copy()
df["transaction_date"] = df["transaction_datetime"].dt.date
catat("7. Tanggal valid", df, f"{n0-len(df)} baris dibuang; {df['transaction_datetime'].min():%d %b %Y} s.d. {df['transaction_datetime'].max():%d %b %Y}")

# --- pemeriksaan sementara langkah 5 (boleh dihapus nanti) ---
print("\nContoh 3 baris, sebelum -> sesudah:")
print(df[["amount_raw", "amount", "admin_fee_raw", "admin_fee_flag"]].head(3).to_string())
print("\nTotal amount: Rp {:,}".format(int(df["amount"].sum())))
print("Transaksi Rp 0 (gratis):", int(df["is_free"].sum()))
print("Admin fee flag:", df["admin_fee_flag"].value_counts(dropna=False).to_dict())
print("Tipe kolom amount:", df["amount"].dtype, "| tipe kolom tanggal:", df["transaction_datetime"].dtype)

# =====================================================================
# 8. EMAIL -> ID ANONIM  (nama, email, HP tidak dibawa ke staging)
# =====================================================================
df["customer_email"] = df["customer_email"].astype("string").str.strip().str.lower()
email_ok = df["customer_email"].str.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", na=False)
n0 = len(df); df = df[email_ok].copy()
catat("8a. Email valid", df, f"{n0-len(df)} baris dibuang")

def anon(email):
    return hashlib.sha256((SALT + email).encode("utf-8")).hexdigest()[:12]
df["customer_anon_id"] = df["customer_email"].map(anon)
catat("8b. ID anonim dibuat", df, f"{df['customer_anon_id'].nunique():,} pelanggan unik")

# 8c. Penanda data meragukan (tidak dibuang kecuali diminta di KONFIGURASI)
df = df.sort_values("transaction_datetime", kind="stable")
df["is_dup_suspect"] = df.duplicated(["customer_email", "transaction_datetime"], keep="first").astype(int)
kupon_up = df["coupon_code"].astype("string").str.strip().str.upper()
df["is_internal_suspect"] = (df["customer_email"].str.match(INTERNAL_EMAIL_REGEX, na=False) |
                             kupon_up.isin(INTERNAL_COUPONS)).astype(int)
catat("8c. Penanda dibuat", df, f"duplikat email+jam: {int(df['is_dup_suspect'].sum())}, dugaan akun/kupon internal: {int(df['is_internal_suspect'].sum())}")
if BUANG_DUPLIKAT_SUSPECT:
    n0 = len(df); df = df[df["is_dup_suspect"] == 0].copy()
    catat("8d. Buang duplikat email+jam", df, f"{n0-len(df)} baris dibuang")
if BUANG_AKUN_INTERNAL:
    n0 = len(df); df = df[df["is_internal_suspect"] == 0].copy()
    catat("8e. Buang akun/kupon internal", df, f"{n0-len(df)} baris dibuang")

# --- pemeriksaan sementara langkah 6 (boleh dihapus nanti) ---
print("\nContoh ID anonim (3 baris pertama):", df["customer_anon_id"].head(3).tolist())
print("Pelanggan unik:", df["customer_anon_id"].nunique())
per = df.groupby("customer_anon_id").size()
print("Jumlah transaksi per pelanggan -> 1x:", int((per == 1).sum()), "| 2x:", int((per == 2).sum()), "| 3x atau lebih:", int((per >= 3).sum()))
print("Dugaan duplikat (email+jam sama):", int(df["is_dup_suspect"].sum()))
print("Dugaan akun/kupon internal:", int(df["is_internal_suspect"].sum()))

# =====================================================================
# 9. CHANNEL AKUISISI  (jawaban 'Dari mana anda mengetahui Gipsy Research?')
# =====================================================================
MAP = {
    "Instagram": "Instagram", "Facebook": "Facebook", "Instagram/ Facebook": "Instagram/Facebook",
    "Media Sosial (IG/ FB/ Tiktok, dll.)": "Media Sosial (umum)",
    "Tiktok": "TikTok", "Youtube": "YouTube", "Iklan": "Iklan", "Website": "Website",
    "Google Search": "Google Search", "Teman/Kerabat": "Referral (Teman/Kerabat)",
    "Universitas": "Universitas/Institusi", "Universitas/Institusi/Perusahaan": "Universitas/Institusi",
    "Email": "Email", "Lainnya": "Lainnya",
}
df["acquisition_channel"] = df["channel_raw"].astype("string").str.strip().map(MAP).fillna("Tidak diketahui")
tak = sorted(set(df.loc[df["acquisition_channel"] == "Tidak diketahui", "channel_raw"].astype(str)))
catat("9. Channel distandarkan", df, f"nilai asli yang jadi 'Tidak diketahui': {tak}")

# --- pemeriksaan sementara langkah 7 (boleh dihapus nanti) ---
print("\nJumlah transaksi per channel (nilai asli -> nilai bersih):")
tabel = df.groupby(["channel_raw", "acquisition_channel"]).size().reset_index(name="jumlah").sort_values("jumlah", ascending=False)
print(tabel.to_string(index=False))
print("\nJumlah kategori channel bersih:", df["acquisition_channel"].nunique())

# =====================================================================
# 10. KOLOM PENDUKUNG
#     Formulir pendaftaran berganti 3 kali, judul kolom Excel tetap, sehingga isi kolom berpindah:
#       v1 (Mei-Des 2025)  : institusi = 'Institusi/Universitas', jurusan = 'Jurusan/...'; profesi & tujuan belum ditanyakan
#       v2 (Jan-Jun 2026)  : institusi = 'Varian Produk', profesi = 'Qty',
#                            jurusan = 'Institusi/Universitas/Perusahaan', tujuan = 'Profesi'
#       v3 (Jul 2026 -)    : institusi = 'Varian Produk' (atau 'Institusi/Universitas/Perusahaan'),
#                            profesi = 'Profesi', jurusan = 'Program Studi/ Bidang Pekerjaan', tujuan = 'Tujuan Penggunaan'
#     Versi ditentukan dari ISI baris (bukan tanggal), supaya baris campuran ikut benar.
# =====================================================================
def _c(x):
    if pd.isna(x): return np.nan
    x = " ".join(html.unescape(str(x)).split())
    return np.nan if x in ("", "-", "nan", "NaN", "None") else x

PROFESI_VALID = {"Mahasiswa", "Dosen", "Guru", "Karyawan", "ASN/TNI/POLRI/Pejabat Lainnya",
                 "Profesi Lainnya", "Wiraswasta", "Pelajar", "Lainnya"}
TUJUAN_AWAL = ("Riset/Penelitian", "Tugas Sekolah/Kuliah", "Proposal & Hibah", "Tugas Kantor & Bisnis",
               "Penulisan Buku", "Pengabdian & Lapangan", "Pembuatan Konten/Materi", "Lainnya")

def isi_profil(d):
    out = []
    for r in d.itertuples():
        V, Q, I, P, S, T, T2 = (_c(getattr(r, k)) for k in
            ["product_variant", "qty_raw", "institution_new", "profession", "study_new", "usage_purpose", "usage_purpose2"])
        Io, So = _c(r.institution_old), _c(r.study_old)
        punya_baru = pd.notna(r.study_new) or pd.notna(r.usage_purpose)
        punya_qty = pd.notna(r.qty_raw)
        if punya_baru and pd.isna(Q):          # v3 sejajar dengan judul kolom
            ver, inst, study, prof, purp = "v3", (V if pd.notna(V) else I), S, P, (T if pd.notna(T) else T2)
        elif punya_baru:                       # v3 campuran: profesi masih di kolom Qty
            ver, inst, study, prof, purp = "v3", V, (S if pd.notna(S) else I), Q, (T if pd.notna(T) else T2)
        elif punya_qty:                        # v2: judul kolom bergeser satu
            ver, inst, study, prof, purp = "v2", V, I, Q, P
        else:                                  # v1: formulir awal
            ver, inst, study, prof, purp = "v1", (Io if pd.notna(Io) else V), So, np.nan, np.nan
        if ver != "v1":                        # kolom lama dipakai bila kolom baru kosong
            inst = inst if pd.notna(inst) else Io
            study = study if pd.notna(study) else So
        if pd.notna(prof) and prof not in PROFESI_VALID: prof = np.nan          # isi nyasar -> kosong
        if pd.notna(purp) and not str(purp).startswith(TUJUAN_AWAL): purp = np.nan
        out.append((ver, inst, study, prof, purp))
    return pd.DataFrame(out, columns=["form_version", "institution", "study_or_occupation", "profession", "usage_purpose"], index=d.index)

prof_df = isi_profil(df)
df = df.drop(columns=["profession", "usage_purpose"]).join(prof_df)
for c in ["product_name", "product_type", "product_variant", "payment_method", "coupon_code"]:
    df[c] = bersih_teks(df[c])
df["coupon_code"] = df["coupon_code"].astype("string").str.upper()
vc = df["form_version"].value_counts().to_dict()
catat("10. Kolom pendukung dirapikan", df, f"versi formulir: {vc}")

# --- pemeriksaan sementara langkah 8 (boleh dihapus nanti) ---
print("\nBaris yang terisi per versi formulir:")
print(df.groupby("form_version")[["institution", "study_or_occupation", "profession", "usage_purpose"]].count().assign(total_baris=df.groupby("form_version").size()).to_string())
print("\nProfesi terbanyak:"); print(df["profession"].value_counts().head(5).to_string())
print("\nTujuan penggunaan terbanyak:"); print(df["usage_purpose"].str.slice(0, 40).value_counts().head(3).to_string())
print("\nContoh 3 baris formulir v2 (institusi, jurusan, profesi):")
print(df[df["form_version"] == "v2"][["institution", "study_or_occupation", "profession"]].head(3).to_string())

# =====================================================================
# 11. VALIDASI  (skrip berhenti kalau ada yang tidak sesuai)
# =====================================================================
assert df["transaction_id"].is_unique,            "Transaction ID tidak unik"
assert df["transaction_id"].notna().all(),        "Ada Transaction ID kosong"
assert df["customer_anon_id"].notna().all(),      "Ada ID anonim kosong"
assert (df["amount"] >= 0).all(),                 "Ada Amount negatif"
assert df["transaction_datetime"].notna().all(),  "Ada tanggal kosong"
assert (df["status"] == "Paid").all(),            "Ada status selain Paid"
print("\nValidasi lulus.")

# =====================================================================
# 12. TABEL AKHIR, SIMPAN CSV + LOG
# =====================================================================
KOLOM = ["transaction_id", "customer_anon_id", "transaction_datetime", "transaction_date",
         "amount", "admin_fee_flag", "channel_fee_flag", "acquisition_channel",
         "product_name", "product_type", "status", "payment_method",
         "coupon_code", "institution", "profession", "study_or_occupation", "usage_purpose",
         "is_free", "is_realigned", "form_version", "is_dup_suspect", "is_internal_suspect"]
stg = df[KOLOM].sort_values("transaction_datetime").reset_index(drop=True)
stg.to_csv(os.path.join(OUT_DIR, "stg_transaksi_bersih.csv"), index=False, encoding="utf-8-sig")
pd.DataFrame(LOG).to_csv(os.path.join(OUT_DIR, "log_cleaning.csv"), index=False, encoding="utf-8-sig")

RINGKAS = {
    "Transaksi bersih": len(stg),
    "Pelanggan unik": stg["customer_anon_id"].nunique(),
    "Total revenue (Rp)": int(stg["amount"].sum()),
    "Transaksi Rp 0 (gratis)": int(stg["is_free"].sum()),
    "Dugaan duplikat (email+jam)": int(stg["is_dup_suspect"].sum()),
    "Dugaan akun/kupon internal": int(stg["is_internal_suspect"].sum()),
    "Periode": f"{stg['transaction_datetime'].min():%d %b %Y} - {stg['transaction_datetime'].max():%d %b %Y}",
}
print("\n=== RINGKASAN ===")
for k, v in RINGKAS.items(): print(f"{k:<28}{v:>20,}" if isinstance(v, (int, np.integer)) else f"{k:<28}{v:>20}")

# --- pemeriksaan sementara langkah 9 (boleh dihapus nanti) ---
print("\nUkuran tabel akhir (baris, kolom):", stg.shape)
print("Ada kolom data pribadi?", any(k in stg.columns for k in ["customer_name", "customer_email", "customer_mobile", "pixel_fbp", "pixel_fbc"]))
print("File tersimpan di:", OUT_DIR)
print(sorted(os.listdir(OUT_DIR)))


# =====================================================================
# 13. MUAT KE STAGING SQL SERVER
#     Tabel stg_transaksi sudah dibuat lewat SSMS (Langkah 10).
# =====================================================================
import urllib.parse

SQL_SERVER   = r"localhost\SQLEXPRESS"
SQL_DATABASE = "GipsyAI_Pro_DW"
SQL_DRIVER   = None          # None = pilih otomatis driver ODBC terbaru yang terpasang
STG_TABLE    = "stg_transaksi"
LOAD_TO_SQL  = True          # True = muat ke SQL Server

def pilih_driver():
    """Pilih 'ODBC Driver NN for SQL Server' dengan nomor tertinggi yang terpasang."""
    import pyodbc
    cocok = [d for d in pyodbc.drivers() if re.match(r"ODBC Driver \d+ for SQL Server", d)]
    if not cocok:
        sys.exit("Driver ODBC for SQL Server belum terpasang. Daftar driver terpasang: " + str(pyodbc.drivers()))
    return max(cocok, key=lambda d: int(re.search(r"\d+", d).group()))

def muat_ke_sql(stg):
    from sqlalchemy import create_engine, text
    drv = SQL_DRIVER or pilih_driver()
    print(f"\nDriver ODBC: {drv}")
    odbc = (f"DRIVER={{{drv}}};SERVER={SQL_SERVER};DATABASE={SQL_DATABASE};"
            f"Trusted_Connection=yes;TrustServerCertificate=yes;")
    url = "mssql+pyodbc:///?odbc_connect=" + urllib.parse.quote_plus(odbc)
    eng = create_engine(url, fast_executemany=True)
    data = stg.copy()
    data = data.astype(object).where(data.notna(), None)          # NaN/NA -> NULL
    with eng.begin() as con:
        con.execute(text(f"DELETE FROM {STG_TABLE}"))              # kosongkan dulu (aman dijalankan ulang)
        data.to_sql(STG_TABLE, con, if_exists="append", index=False, chunksize=500)
        n, rev = con.execute(text(f"SELECT COUNT(*), SUM(amount) FROM {STG_TABLE}")).one()
    print(f"Terisi di SQL Server: {n:,} baris, total amount Rp {int(rev):,}")
    assert n == len(stg) and int(rev) == int(stg['amount'].sum()), "Jumlah di SQL Server tidak cocok dengan pandas!"
    print("Verifikasi jumlah baris dan total amount: COCOK")

if LOAD_TO_SQL:
    muat_ke_sql(stg)
else:
    print("\nLOAD_TO_SQL = False: tidak memuat ke SQL Server.")