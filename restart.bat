@echo off
echo ================================================================
echo           SISTEMA DE GESTAO DE SUGESTOES v2.0
echo                  REINICIAR SERVIDOR
echo ================================================================
echo.

echo [INFO] Parando servidor existente...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im pythonw.exe >nul 2>&1
timeout /t 2 >nul

echo [INFO] Iniciando servidor com novas configuracoes...
echo.

call run.bat
