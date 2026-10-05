#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
VENV_DIR="${VENV_DIR:-$REPO_DIR/.venv}"
BIND_ADDRESS="${BIND_ADDRESS:-127.0.0.1}"
PORT="${PORT:-8520}"

if [[ ! -x "$VENV_DIR/bin/streamlit" ]]; then
  printf 'Streamlit não encontrado em %s\n' "$VENV_DIR" >&2
  printf 'Crie o ambiente virtual e instale requirements.txt antes de iniciar.\n' >&2
  exit 1
fi

# OCR externo é opcional para PDFs nativos e obrigatório para PDFs digitalizados.
export TESSERACT_CONFIG="${TESSERACT_CONFIG:---psm 3}"
export OCR_DPI="${OCR_DPI:-160}"

cd "$REPO_DIR"
exec "$VENV_DIR/bin/streamlit" run app/main.py \
  --server.address "$BIND_ADDRESS" \
  --server.port "$PORT" \
  --server.headless true \
  --browser.gatherUsageStats false
