# Scripts\build_exe.ps1 - Empaqueta DataClean en un .exe con PyInstaller.
#
# Uso (desde la raiz del repositorio):
#   .\scripts\build_exe.ps1
#
# Requisitos:
#   - Entorno virtual en .venv con Python 3.13.x (obligatorio).
#   - pyinstaller instalado en el venv (ver requirements.txt).

$ErrorActionPreference = "Stop"

# Raiz del repositorio (dos niveles por encima de este script).
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

# --- (a) Verificar el venv y la version de Python (3.13.x) ---
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Error "No se encontro el entorno virtual en '$venvPython'. Crea el venv con Python 3.13 antes de compilar."
}

$pyVersion = & $venvPython --version 2>&1  # p. ej. "Python 3.13.15"
if ($pyVersion -notmatch "^Python 3\.13\.") {
    Write-Error "Se requiere Python 3.13.x (obligatorio para PyInstaller); el venv tiene: $pyVersion. Recrea el .venv con Python 3.13."
}
Write-Host "[OK] Python del venv: $pyVersion"

if (-not (Test-Path (Join-Path $root "build\dataclean.spec"))) {
    Write-Error "No se encontro 'build\dataclean.spec'. Ejecuta este script desde la raiz del repositorio."
}

# --- (b) Ejecutar PyInstaller con el spec commiteado ---
Write-Host "[..] Compilando con PyInstaller (esto puede tardar varios minutos)..."
& $venvPython -m PyInstaller build\dataclean.spec --clean --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller fallo con codigo de salida $LASTEXITCODE."
}

# --- (c) Verificar el resultado ---
$exe = Join-Path $root "dist\DataClean\DataClean.exe"
if (-not (Test-Path $exe)) {
    Write-Error "El build termino pero no se encontro '$exe'. Revisa el log de PyInstaller."
}

$sizeMB = [math]::Round((Get-Item $exe).Length / 1MB, 1)
Write-Host "[OK] Ejecutable generado correctamente:"
Write-Host "     $exe ($sizeMB MB)"
