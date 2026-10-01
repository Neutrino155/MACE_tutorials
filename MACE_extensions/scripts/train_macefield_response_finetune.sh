#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -z "${INITIAL_MODEL:-}" ]]; then
  echo "Set INITIAL_MODEL to a scratch-trained MACEField .model checkpoint." >&2
  exit 2
fi
export OUT_DIR="${OUT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)/MACE_extensions/models/macefield_response_finetune}"
export EPOCHS="${EPOCHS:-80}"
export BATCH_SIZE="${BATCH_SIZE:-32}"
# Keep the energy/force surface near its fitted basin while polarization labels
# sharpen the field response.
export LR="${LR:-0.00005}"
export ENERGY_WEIGHT="${ENERGY_WEIGHT:-1}"
export FORCES_WEIGHT="${FORCES_WEIGHT:-100}"
export POLARIZATION_WEIGHT="${POLARIZATION_WEIGHT:-0.05}"
# Freeze the shared zero-field representation and tune the field response.
export FREEZE="${FREEZE:-7}"
source "$SCRIPT_DIR/common.sh"
bash "$SCRIPT_DIR/train_macefield.sh"
MODEL_PATH="$OUT_DIR/MACEField-Landau.model"
"$PYTHON" "$ROOT/MACE_extensions/scripts/calibrate_macefield_energy_offset.py" \
  --model "$MODEL_PATH" \
  --train-file "$DATA/macefield_batio3_toy_train.extxyz"
