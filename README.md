# GipsyAI Pro: Dashboard Channel Akuisisi Pelanggan

Dashboard Business Intelligence untuk analisis channel akuisisi pelanggan
dengan K-Means Clustering (RFM) pada GipsyAI Pro, PT Gipsy Riset Nusantara.

## Menjalankan
- Mode lokal (SQL Server): `python -m streamlit run app.py`
- Mode online (snapshot CSV): atur `sumber_data = "file"` pada secrets.

Data pelanggan memakai ID anonim. Akun login diatur lewat `.streamlit/secrets.toml`
(tidak termasuk dalam repo).