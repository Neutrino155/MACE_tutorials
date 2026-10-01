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
# Keep the shared energy surface near its fitted energy/force basin while the
# higher-order response derivatives are introduced.
export LR="${LR:-0.00005}"
export ENERGY_WEIGHT="${ENERGY_WEIGHT:-1}"
export FORCES_WEIGHT="${FORCES_WEIGHT:-100}"
export POLARIZATION_WEIGHT="${POLARIZATION_WEIGHT:-5}"
export BECS_WEIGHT="${BECS_WEIGHT:-2}"
export POLARIZABILITY_WEIGHT="${POLARIZABILITY_WEIGHT:-1}"
# MACE-Field's field adapters are outside the standard embedding, interaction,
# product, and readout stacks. Freeze level 7 trains only those adapters, so
# the zero-field energy and force surface fitted in stage one is preserved.
export FREEZE="${FREEZE:-7}"
export COMPUTE_RESPONSES=1
source "$SCRIPT_DIR/common.sh"
bash "$SCRIPT_DIR/train_macefield.sh"
MODEL_PATH="$OUT_DIR/MACEField-Landau.model"
"$PYTHON" "$ROOT/MACE_extensions/scripts/calibrate_macefield_energy_offset.py" \
  --model "$MODEL_PATH" \
  --train-file "$DATA/macefield_batio3_toy_train.extxyz"
