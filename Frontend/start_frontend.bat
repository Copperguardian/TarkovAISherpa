@echo off
:: Tarkov Sherpa — Frontend (Streamlit)
:: Activa el entorno conda y arranca la interfaz Streamlit.
:: Asegurate de que el backend (start_backend.bat) ya esta corriendo.

call conda activate langchain-env

echo.
echo  [Tarkov Sherpa] Frontend arrancando en http://localhost:8501
echo  Pulsa Ctrl+C para detener.
echo.

streamlit run app.py
