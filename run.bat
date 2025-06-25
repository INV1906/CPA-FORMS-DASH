@echo off
chcp 65001 >nul
echo ========================================
echo Sistema de Gestao de Sugestoes v2.0
echo ========================================
echo.
echo Iniciando o servidor FastAPI...
echo.
echo Acesse: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo Login: admin@sistema.com  
echo Senha: admin123
echo.
echo Pressione Ctrl+C para parar o servidor
echo.

.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

pause
