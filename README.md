# GipsyAI Pro: Dashboard Channel Akuisisi Pelanggan

## Dashboard online

Versi online dashboard dapat dibuka di:

**https://gipsyai-pro-dashboard-4mxfpbmhumcibchymzk9df.streamlit.app**

- Login memakai akun yang diberikan peneliti (username dan password tidak dicantumkan di repositori ini).
- Versi online membaca **snapshot CSV** di folder `data_dashboard/`. Data memakai ID pelanggan anonim, tanpa nama, email, atau nomor telepon.
- Versi lokal membaca langsung dari SQL Server `GipsyAI_Pro_DW`. Mode ditentukan oleh `sumber_data` di `.streamlit/secrets.toml` (`"sql"` atau `"file"`).
- Snapshot dibuat dengan `python ekspor_snapshot.py`. Setelah snapshot diperbarui, commit dan push, lalu aplikasi online menyesuaikan otomatis.

Dashboard Business Intelligence untuk analisis channel akuisisi pelanggan
dengan K-Means Clustering (RFM) pada GipsyAI Pro, PT Gipsy Riset Nusantara.

## Menjalankan
- Mode lokal (SQL Server): `python -m streamlit run app.py`
- Mode online (snapshot CSV): atur `sumber_data = "file"` pada secrets.

Data pelanggan memakai ID anonim. Akun login diatur lewat `.streamlit/secrets.toml`
(tidak termasuk dalam repo).

