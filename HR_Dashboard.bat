@echo off
cd /d "D:\Work\Resume_Line"
call venv\Scripts\activate
start /min venv\Scripts\python.exe -m streamlit run dashboard.py