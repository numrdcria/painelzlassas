$ErrorActionPreference = 'Stop'

$project = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $project

function Get-PythonCommand {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        return 'py'
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        return 'python'
    }
    throw 'Python nao foi encontrado. Instale o Python 3.11+ e marque a opcao Add Python to PATH.'
}

$pythonCmd = Get-PythonCommand
$venvPython = Join-Path $project '.venv\Scripts\python.exe'
$waitressExe = Join-Path $project '.venv\Scripts\waitress-serve.exe'

if (-not (Test-Path $venvPython)) {
    Write-Host '[1/6] Criando ambiente virtual...'
    & $pythonCmd -m venv .venv
}

Write-Host '[2/6] Atualizando pip...'
& $venvPython -m pip install --upgrade pip

Write-Host '[3/6] Instalando dependencias...'
& $venvPython -m pip install -r requirements.txt

if (-not (Test-Path '.env')) {
    Write-Host '[4/6] Criando .env...'
    Copy-Item '.env.example' '.env'
}

Write-Host '[5/6] Ajustando .env para SQLite local...'
$envContent = Get-Content '.env' | Where-Object { $_ -notmatch '^DATABASE_URL=' }
$envContent = $envContent | Where-Object { $_ -notmatch '^APP_BASE_URL=' }
$envContent += 'APP_BASE_URL=http://127.0.0.1:8000'
Set-Content '.env' $envContent

Write-Host '[6/6] Inicializando banco...'
& $venvPython 'scripts\init_db.py'

Write-Host ''
Write-Host 'Sistema iniciado em http://127.0.0.1:8000' -ForegroundColor Green
Write-Host 'Login inicial: admin@empresa.com / 123456' -ForegroundColor Yellow
Write-Host ''

if (Test-Path $waitressExe) {
    & $waitressExe --host=127.0.0.1 --port=8000 wsgi:app
} else {
    & $venvPython -m flask --app wsgi run --host=127.0.0.1 --port=8000
}
