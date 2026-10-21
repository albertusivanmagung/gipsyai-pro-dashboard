@echo off
cd /d "E:\Skripsi\GipsyAI Pro Skripsi"
call .venv\Scripts\activate
python -m streamlit run app.py
pause