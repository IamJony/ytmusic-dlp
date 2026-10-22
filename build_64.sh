#!/usr/bin/env bash
# build_64.sh — Empaqueta ytmusic-dlp para Linux 64 bits SIN mpv/ffmpeg.
# El usuario destino necesita: sudo apt install mpv ffmpeg
#
# ⚠️  REGLA DE ORO: este script NUNCA toca build/ytmusic-dlp-i686/
#     ni dist/ytmusic-dlp-i686. Si algo intenta hacerlo, aborta.
set -euo pipefail
cd "$(dirname "$0")"

# ---------------------------------------------------------------------------
# Rutas
# ---------------------------------------------------------------------------
BIN32="dist/ytmusic-dlp-i686"
BIN64="dist/ytmusic-dlp-x86_64"
BUILD64="build/ytmusic-dlp-x86_64"
SPEC64="ytmusic-dlp-x86_64.spec"

# Artefactos de 32 bits PROHIBIDOS de tocar
PROTECTED_PREFIXES=(
    "build/ytmusic-dlp-i686"
    "dist/ytmusic-dlp-i686"
)

# ---------------------------------------------------------------------------
# Guardia: aborta si $1 es (o está dentro de) un artefacto protegido
# ---------------------------------------------------------------------------
assert_not_protected() {
    local p="$1"
    for prot in "${PROTECTED_PREFIXES[@]}"; do
        if [ "$p" = "$prot" ] || [[ "$p" == "$prot"/* ]]; then
            echo "ERROR CRITICO: intento de tocar artefacto de 32 bits: $p"
            echo "               Esto NUNCA debe ocurrir. Abortando."
            exit 99
        fi
    done
}

# Borrado seguro: solo borra si NO es un artefacto protegido
safe_rm() {
    local p="$1"
    assert_not_protected "$p"
    if [ ! -e "$p" ]; then
        return 0
    fi
    echo "  Borrando: $p"
    # Dar permisos por si quedaron de otra ejecución
    chmod -R u+rwX "$p" 2>/dev/null || true
    if ! rm -rf "$p" 2>/dev/null; then
        echo "  ! No se pudo borrar $p, renombrando..."
        mv "$p" "${p}.old.$(date +%s)" 2>/dev/null || {
            echo "  ERROR: no se pudo limpiar $p"
            exit 1
        }
    fi
}

# ---------------------------------------------------------------------------
# 0. Verificar entorno
# ---------------------------------------------------------------------------
echo "=== 0. Verificando entorno ==="
if ! file -L "$(command -v python3)" | grep -q "64-bit"; then
    echo "ERROR: Python no es de 64 bits. Abortando."
    exit 1
fi
echo "  Python: $(python3 --version)"
echo "  Arquitectura: 64-bit"

if [ -e "build/ytmusic-dlp-i686" ] || [ -e "dist/ytmusic-dlp-i686" ]; then
    echo "  Detectado artefacto de 32 bits (NO se tocará):"
    [ -e "build/ytmusic-dlp-i686" ] && echo "    - build/ytmusic-dlp-i686/"
    [ -e "dist/ytmusic-dlp-i686" ]  && echo "    - dist/ytmusic-dlp-i686"
else
    echo "  (No hay artefactos de 32 bits previos)"
fi

# ---------------------------------------------------------------------------
# 1. Limpieza — SOLO artefactos de 64 bits
# ---------------------------------------------------------------------------
echo ""
echo "=== 1. Limpiando SOLO artefactos de 64 bits ==="

# __pycache__ y .pyc son seguros (no son 32 ni 64)
find . -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true
find . -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete 2>/dev/null || true

# ⚠️ NUNCA `rm -rf build` ni `rm -rf dist`.
# Solo se borra el directorio build de la build 64 actual.
safe_rm "$BUILD64"
rm -f "$SPEC64"
safe_rm "$BIN64"

mkdir -p assets
touch assets/.gitkeep

# Verificación post-limpieza: 32 bits intacto
echo ""
echo "  Verificando que 32 bits sigue intacto..."
OK32=1
if [ -e "build/ytmusic-dlp-i686" ]; then
    echo "    OK: build/ytmusic-dlp-i686/ sigue presente"
else
    echo "    (build/ytmusic-dlp-i686/ no existía antes, ok)"
fi
if [ -f "dist/ytmusic-dlp-i686" ]; then
    echo "    OK: dist/ytmusic-dlp-i686 sigue presente ($(du -h dist/ytmusic-dlp-i686 | cut -f1))"
else
    OK32=0
    echo "    (dist/ytmusic-dlp-i686 no existía antes)"
fi
if [ "$OK32" -eq 0 ] && [ -e "build/ytmusic-dlp-i686" ]; then
    echo "    ADVERTENCIA: existe build de 32 bits pero falta el binario dist."
fi

# ---------------------------------------------------------------------------
# 2. Dependencias del sistema
# ---------------------------------------------------------------------------
echo ""
echo "=== 2. Verificando dependencias del sistema ==="
for cmd in mpv ffmpeg; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "  ADVERTENCIA: '$cmd' no esta instalado en este sistema."
        echo "  El binario funcionara igual, pero el usuario destino lo necesitara."
        echo "  Instala aqui con: sudo apt install mpv ffmpeg"
    else
        echo "  OK: $cmd -> $(command -v "$cmd")"
    fi
done

# ---------------------------------------------------------------------------
# 3. venv 64 bits
# ---------------------------------------------------------------------------
echo ""
echo "=== 3. Creando venv (64 bits) ==="
VENV_DIR="/opt/ytmusic-venv-64"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install --upgrade yt-dlp pyinstaller python-mpv plyer pillow

echo "  yt-dlp: $(yt-dlp --version)"
echo "  pyinstaller: $(pyinstaller --version)"

# ---------------------------------------------------------------------------
# 4. Compilar — SIN --clean (--clean borra build/ COMPLETO)
# ---------------------------------------------------------------------------
echo ""
echo "=== 4. Compilando con PyInstaller (64 bits) ==="
echo "  (Sin --clean: borraría build/ completo, incluida la 32 bits)"

pyinstaller \
    --onefile \
    --name ytmusic-dlp-x86_64 \
    --windowed \
    --add-data "src:src" \
    --add-data "assets:assets" \
    --hidden-import=plyer.platforms.linux.notification \
    --hidden-import=PIL._tkinter_finder \
    --collect-all yt_dlp \
    --distpath dist \
    --workpath build \
    --specpath . \
    src/main.py

# Verificación post-build: 32 bits intacto
echo ""
echo "  Verificando que 32 bits sigue intacto tras PyInstaller..."
if [ -e "build/ytmusic-dlp-i686" ] || [ -f "dist/ytmusic-dlp-i686" ]; then
    echo "    OK"
else
    echo "    ADVERTENCIA: artefactos de 32 bits no encontrados (¿existían antes?)"
fi

# ---------------------------------------------------------------------------
# 5. Verificación del resultado 64 bits
# ---------------------------------------------------------------------------
echo ""
echo "=== 5. Verificando resultado ==="
if [ ! -f "$BIN64" ]; then
    echo "ERROR: no se genero el binario de 64 bits"
    exit 1
fi
chmod +x "$BIN64"
SIZE=$(du -h "$BIN64" | cut -f1)
TYPE=$(file "$BIN64")
echo "  Tamano: $SIZE"
echo "  Tipo: $TYPE"

if echo "$TYPE" | grep -q "64-bit"; then
    echo "  OK: binario de 64 bits"
else
    echo "  ERROR: el binario NO es de 64 bits"
    exit 1
fi

echo ""
if [ -f "$BIN32" ]; then
    echo "  Binario de 32 bits preservado: $BIN32 ($(du -h "$BIN32" | cut -f1))"
    file "$BIN32"
else
    echo "  ADVERTENCIA: el binario de 32 bits no existe en $BIN32"
fi

# ---------------------------------------------------------------------------
# 6. Resumen
# ---------------------------------------------------------------------------
echo ""
echo "=============================================="
echo " Binarios en dist/:"
ls -lh dist/
echo "=============================================="
echo " Probar 64 bits:"
echo "   ./dist/ytmusic-dlp-x86_64"
echo ""
echo " Dependencias del sistema (requeridas):"
echo "   sudo apt install mpv ffmpeg"
