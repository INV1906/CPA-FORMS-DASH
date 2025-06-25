@echo off
chcp 65001 >nul
REM Setup script para o Sistema de Gestao de Sugestoes
REM Este script configura o ambiente e inicia o sistema

echo Sistema de Gestao de Sugestoes - Setup
echo ========================================

REM Verificar se Python esta instalado
REM Tentar diferentes comandos do Python
set PYTHON_CMD=
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    goto :python_found
)

python3 --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=python3
    goto :python_found
)

py --version >nul 2>&1
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    goto :python_found
)

REM Se chegou aqui, Python nao foi encontrado
echo Python nao encontrado. Por favor, instale Python 3.8 ou superior.
echo.
echo Opcoes de instalacao:
echo 1. Baixe do site oficial: https://python.org/downloads
echo 2. Use o Microsoft Store: procure por "Python 3"
echo 3. Use o gerenciador de pacotes: winget install Python.Python.3
pause
exit /b 1

:python_found
for /f "tokens=*" %%i in ('%PYTHON_CMD% --version') do set python_version=%%i
echo Python encontrado: %python_version%

REM Verificar se ja estamos em um ambiente virtual
if defined VIRTUAL_ENV (
    echo Ambiente virtual ja ativo: %VIRTUAL_ENV%
    set VENV_PYTHON=%VIRTUAL_ENV%\Scripts\python.exe
    goto :install_deps
)

REM Criar ambiente virtual se não existir
if not exist ".venv" (
    echo Criando ambiente virtual...
    %PYTHON_CMD% -m venv .venv
    if %errorlevel% neq 0 (
        echo Erro ao criar ambiente virtual
        pause
        exit /b 1
    )
)

REM Ativar ambiente virtual
echo Ativando ambiente virtual...
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    set VENV_PYTHON=.venv\Scripts\python.exe
) else (
    echo Erro: ambiente virtual nao encontrado
    pause
    exit /b 1
)

:install_deps
REM Instalar dependências
echo Instalando dependencias...

REM Atualizar pip primeiro
if defined VENV_PYTHON (
    %VENV_PYTHON% -m pip install --upgrade pip
) else (
    %PYTHON_CMD% -m pip install --upgrade pip
)

REM Instalar dependências do projeto
echo Instalando dependencias...
if defined VENV_PYTHON (
    %VENV_PYTHON% -m pip install -r requirements.txt
    set INSTALL_RESULT=%errorlevel%
) else (
    %PYTHON_CMD% -m pip install -r requirements.txt
    set INSTALL_RESULT=%errorlevel%
)

if %INSTALL_RESULT% neq 0 (
    echo Erro ao instalar dependencias
    echo.
    echo SOLUCOES POSSIVEIS:
    echo 1. Use Python 3.11 ou 3.12 para maior compatibilidade
    echo    Download: https://www.python.org/downloads/
    echo 2. Execute: pip install --upgrade pip
    echo 3. Execute: pip install firebase-admin google-cloud-firestore fastapi uvicorn
    echo.
    echo Para Python 3.13, execute o comando alternativo:
    echo python -m pip install --no-build-isolation firebase-admin
    echo.
    pause
    exit /b 1
)

REM Verificar se arquivo .env existe
if not exist ".env" (
    echo ⚙️  Criando arquivo de configuração...
    copy .env.example .env
    echo 📝 Por favor, edite o arquivo .env com suas configurações antes de continuar.
    echo    Especialmente as configurações de banco de dados.
    pause
)

REM Configurar banco de dados (Firebase)
echo Configurando banco de dados Firebase...
if defined VENV_PYTHON (
    %VENV_PYTHON% backend\database\setup_database.py
    set DB_RESULT=%errorlevel%
) else (
    %PYTHON_CMD% backend\database\setup_database.py
    set DB_RESULT=%errorlevel%
)

if %DB_RESULT% equ 0 (
    echo ✅ Firebase configurado com sucesso!
) else (
    echo ⚠️ Aviso: Erro ao configurar Firebase
    echo O sistema pode funcionar em modo demo
    echo Verifique as credenciais no arquivo .env se necessário
)

REM Criar diretórios necessários
echo Criando diretorios...
if not exist "data\exports" mkdir data\exports
if not exist "data\logs" mkdir data\logs
if not exist "data\backups" mkdir data\backups

echo.
echo Setup concluido com sucesso!
echo.
echo Proximos passos:
echo 1. Configure as integracoes no arquivo .env (opcional)
echo 2. Execute o sistema: run.bat
echo 3. Acesse http://localhost:8000 no seu navegador
echo 4. API Docs: http://localhost:8000/docs
echo 5. Login: admin@sistema.com / admin123
echo.
echo Comandos uteis:
echo - Iniciar sistema: run.bat
echo - Verificar banco: python backend\database\setup_database.py --verify
echo - Acessar documentacao: http://localhost:8000/docs (após iniciar)
echo.
echo Documentacao completa disponivel no README.md
echo.
pause
