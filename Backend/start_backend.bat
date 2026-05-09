@echo off
:: Tarkov Sherpa — Backend (FastAPI)
:: Activa el entorno conda y arranca el servidor uvicorn.

call conda activate langchain-env

echo.
echo  [Tarkov Sherpa] Backend arrancando en http://localhost:8000
echo  Pulsa Ctrl+C para detener.
echo.

uvicorn main:app --reload --port 8000
