#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Jointly learn all labels derived from the analytic electric enthalpy. This
# is the primary from-scratch route used by the MACEField tutorial.
export OUT_DIR="${OUT_DIR:-$(cd "$SCRIPT_DIR/../.." && pwd)/MACE_extensions/models/macefield_joint}"
export EPOCHS="${EPOCHS:-120}"
export BATCH_SIZE="${BATCH_SIZE:-32}"
export LR="${LR:-0.005}"
export ENERGY_WEIGHT="${ENERGY_WEIGHT:-1}"
export FORCES_WEIGHT="${FORCES_WEIGHT:-100}"
export POLARIZATION_WEIGHT="${POLARIZATION_WEIGHT:-0.01}"
export BECS_WEIGHT="${BECS_WEIGHT:-0.01}"
export POLARIZABILITY_WEIGHT="${POLARIZABILITY_WEIGHT:-0.01}"
export FREEZE="${FREEZE:-0}"
export COMPUTE_RESPONSES=1

source "$SCRIPT_DIR/common.sh"
bash "$SCRIPT_DIR/train_macefield.sh"
MODEL_PATH="$OUT_DIR/MACEField-Landau.model"
"$PYTHON" "$ROOT/MACE_extensions/scripts/calibrate_macefield_energy_offset.py" \
  --model "$MODEL_PATH" \
  --train-file "$DATA/macefield_batio3_toy_train.extxyz"
