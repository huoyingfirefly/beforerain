@echo off
cd /d "%~dp0"
title Before Rain - Setup
echo.
echo ================================================
echo   Before Rain - Full Auto Setup
echo ================================================
echo.

:: =============================================
:: Step 0: Find or install Python
:: =============================================
echo [0/5] Checking Python...
set PYEXE=

if exist "%LOCALAPPDATA%\Python\bin\python.exe"      set PYEXE=%LOCALAPPDATA%\Python\bin\python.exe
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set PYEXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe
if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set PYEXE=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
if exist "C:\Python313\python.exe"                   set PYEXE=C:\Python313\python.exe
if exist "C:\Python312\python.exe"                   set PYEXE=C:\Python312\python.exe
if exist "C:\Python311\python.exe"                   set PYEXE=C:\Python311\python.exe
if exist "C:\Program Files\Python313\python.exe"     set PYEXE=C:\Program Files\Python313\python.exe
if exist "C:\Program Files\Python312\python.exe"     set PYEXE=C:\Program Files\Python312\python.exe

if "%PYEXE%"=="" (
    where python.exe >nul 2>&1
    if not errorlevel 1 set PYEXE=python
)
if "%PYEXE%"=="" (
    where python3.exe >nul 2>&1
    if not errorlevel 1 set PYEXE=python3
)

if not "%PYEXE%"=="" (
    echo Found: %PYEXE%
    %PYEXE% --version
    echo OK
    goto :step1
)

:: No Python found - go install it
goto :install_python

:install_python
echo Python not found.
echo.
echo Downloading Python 3.13 (~25MB)...
echo This may take 1-3 minutes depending on your network.
echo.

set "PI=%TEMP%\python-3.13.2-amd64.exe"
set "PYURL=https://www.python.org/ftp/python/3.13.2/python-3.13.2-amd64.exe"

:: Method 1: curl.exe (built into Win10+)
curl.exe --version >nul 2>&1
if not errorlevel 1 (
    echo Using curl to download...
    curl.exe -L -o "%PI%" "%PYURL%" --progress-bar
    if exist "%PI%" goto :run_installer
)

:: Method 2: powershell fallback
echo curl not available, trying PowerShell...
powershell -Command "Invoke-WebRequest -Uri '%PYURL%' -OutFile '%PI%'"
if exist "%PI%" goto :run_installer

:: Method 3: winget fallback
echo PowerShell failed, trying winget...
winget --version >nul 2>&1
if not errorlevel 1 (
    winget install Python.Python.3.13 --accept-package-agreements --accept-source-agreements --silent
    if not errorlevel 1 (
        echo Python installed! Please re-run deploy.bat
        pause
        exit /b 0
    )
)

:: All methods failed
echo.
echo [ERROR] Automatic install failed.
echo Please install Python manually:
echo https://www.python.org/downloads/
echo (Check "Add Python to PATH" during install!)
start https://www.python.org/downloads/
pause
exit /b 1

:run_installer
echo.
echo Download complete. Installing silently...
"%PI%" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
del "%PI%" 2>nul
echo.
echo Python installed! Please close this window and re-run deploy.bat
pause
exit /b 0

:: =============================================
:: Step 1: Check project files
:: =============================================
:step1
echo.
echo [1/5] Checking project files...
if exist "%~dp0api.py" (
    echo OK - project files found
    goto :step2
)

echo Project files not found. Cloning repo...
git --version >nul 2>&1
if errorlevel 1 (
    echo Git not found. Installing via winget...
    winget install Git.Git --accept-package-agreements --accept-source-agreements
    if errorlevel 1 (
        echo Cannot install Git. Download the project manually:
        echo https://gitee.com/fire-flies/beforerain
        start https://gitee.com/fire-flies/beforerain
        pause
        exit /b 1
    )
    echo Git installed! Please re-run deploy.bat
    pause
    exit /b 0
)

echo Trying GitHub...
git clone https://github.com/huoyingfirefly/beforerain.git beforerain 2>nul
if errorlevel 1 (
    echo GitHub failed, trying Gitee...
    git clone https://gitee.com/fire-flies/beforerain.git beforerain
    if errorlevel 1 (
        echo Clone failed. Download manually:
        echo https://gitee.com/fire-flies/beforerain
        start https://gitee.com/fire-flies/beforerain
        pause
        exit /b 1
    )
)
cd /d "%~dp0beforerain"
echo OK - cloned successfully

:step2
:: =============================================
:: Step 2: Setup .env config
:: =============================================
echo.
echo [2/5] Checking config...
if exist "%~dp0.env" (
    echo OK - .env exists
    goto :step3
)

if exist "%~dp0.env.example" (
    copy "%~dp0.env.example" "%~dp0.env" >nul
) else (
    (
echo DEEPSEEK_API_KEY=your_api_key_here
echo DEEPSEEK_BASE_URL=https://api.siliconflow.cn/v1
echo DEEPSEEK_MODEL=deepseek-chat
echo EMBED_API_KEY=your_api_key_here
echo EMBED_BASE_URL=https://api.siliconflow.cn/v1
echo EMBED_MODEL=BAAI/bge-large-zh-v1.5
    ) > "%~dp0.env"
)

echo.
echo ================================================
echo   API KEYS REQUIRED (free registration):
echo.
echo   1. DeepSeek - narrative AI
echo      https://platform.deepseek.com
echo.
echo   2. SiliconFlow - RAG embedding
echo      https://cloud.siliconflow.cn
echo ================================================
echo.
echo Opening registration pages and .env file...
start notepad "%~dp0.env"
start https://platform.deepseek.com
start https://cloud.siliconflow.cn
echo.
echo After filling in your keys, press any key...
pause >nul

:step3
:: =============================================
:: Step 3: Install Python dependencies
:: =============================================
echo.
echo [3/5] Installing Python packages...
%PYEXE% -m pip install --upgrade pip -q

:: Try PyPI then mirrors
echo Trying PyPI...
%PYEXE% -m pip install -r "%~dp0requirements.txt" -q
if not errorlevel 1 goto :deps_done

echo Trying Tsinghua mirror...
%PYEXE% -m pip install -r "%~dp0requirements.txt" -q -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn
if not errorlevel 1 goto :deps_done

echo Trying Aliyun mirror...
%PYEXE% -m pip install -r "%~dp0requirements.txt" -q -i https://mirrors.aliyun.com/pypi/simple --trusted-host mirrors.aliyun.com
if not errorlevel 1 goto :deps_done

echo Trying USTC mirror...
%PYEXE% -m pip install -r "%~dp0requirements.txt" -q -i https://pypi.mirrors.ustc.edu.cn/simple --trusted-host pypi.mirrors.ustc.edu.cn
if not errorlevel 1 goto :deps_done

echo [ERROR] All PyPI mirrors failed.
echo Check your network connection.
pause
exit /b 1

:deps_done
echo OK

:: =============================================
:: Step 4: Check RAG index
:: =============================================
echo.
echo [4/5] Checking RAG index...
:: Strip trailing backslash to avoid Python string escape issues
set "HERE=%~dp0"
if "%HERE:~-1%"=="\" set "HERE=%HERE:~0,-1%"
%PYEXE% -c "import sys; sys.path.insert(0, r'%HERE%'); from rag_lite import is_indexed; exit(0 if is_indexed() else 1)" >nul 2>&1
if errorlevel 1 (
    echo Index not found, rebuilding...
    %PYEXE% -m pip install chromadb -q -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn 2>nul
    if errorlevel 1 (
        %PYEXE% -m pip install chromadb -q
    )
    %PYEXE% -c "import sys; sys.path.insert(0, r'%HERE%'); from rag_engine import index_lore; n = index_lore(r'%HERE%\\world_lore_full.txt'); print(f'Indexed {n} chunks')"
)
echo OK

:: =============================================
:: Step 5: Start server
:: =============================================
echo.
echo [5/5] Starting server...
echo.
echo ================================================
echo   http://localhost:8000       Main Menu
echo   http://localhost:8000/game  Game Page
echo   http://localhost:8000/docs  API Docs
echo   Press Ctrl+C to stop
echo ================================================
echo.

%PYEXE% "%~dp0api.py"
pause
