@echo off
echo ================================================================
echo             VERIFICACAO DE STATUS FIREBASE
echo         Sistema de Gestao de Sugestoes v2.0
echo ================================================================
echo.

echo [INFO] Verificando configuracao atual...
echo.

REM Verificar configurações do .env
echo ====== CONFIGURACAO FIREBASE ======
findstr /i "FIREBASE_" .env

echo.
echo ====== ARQUIVOS DE CREDENCIAIS ======
if exist "config\firebase-service-account.json" (
    echo [OK] Arquivo de credenciais ENCONTRADO
    set "CRED_FILE=true"
) else (
    echo [INFO] Arquivo de credenciais NAO ENCONTRADO
    set "CRED_FILE=false"
)

echo.
echo ====== STATUS DA API ======
echo [INFO] Consultando API para status atual...

REM Fazer requisição HTTP para verificar status
curl -s http://localhost:8000/api/system/health > temp_health.json 2>nul

if exist temp_health.json (
    echo [OK] API respondendo
    echo.
    echo Resposta da API:
    type temp_health.json
    del temp_health.json
) else (
    echo [AVISO] API nao esta respondendo
    echo Certifique-se de que o servidor esta rodando
)

echo.
echo ====== ANALISE DO MODO ATUAL ======

REM Verificar se está em modo demo
findstr /i "FIREBASE_PRIVATE_KEY_ID" .env | findstr /i "dummy" >nul
if errorlevel 1 (
    if "%CRED_FILE%"=="true" (
        echo [STATUS] Modo: PRODUCAO ^(arquivo de credenciais^)
    ) else (
        findstr /i "FIREBASE_PRIVATE_KEY_ID=" .env | findstr /v "^#" | findstr /v "FIREBASE_PRIVATE_KEY_ID=$" >nul
        if not errorlevel 1 (
            echo [STATUS] Modo: PRODUCAO ^(variaveis de ambiente^)
        ) else (
            echo [STATUS] Modo: DEMO ^(credenciais vazias^)
        )
    )
) else (
    echo [STATUS] Modo: DEMO ^(credenciais dummy^)
)

echo.
echo ================================================================
echo                    RESUMO DO STATUS
echo ================================================================
echo.
echo Firebase Habilitado: 
findstr /i "FIREBASE_ENABLED" .env
echo.
echo Project ID: 
findstr /i "FIREBASE_PROJECT_ID" .env
echo.
echo Arquivo de Credenciais: %CRED_FILE%
echo.
echo Para mudar para producao: firebase_manager.bat
echo Para verificar detalhes: http://localhost:8000/api/system/health
echo.
pause
