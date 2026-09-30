#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
"$PYTHON" "$ROOT/MACE_extensions/scripts/bootstrap.py" --feature="base"
OUT="${OUT_DIR:-$ROOT/MACE_extensions/models/atomicdipoles}"
mkdir -p "$OUT"
"$PYTHON" "$SOURCE_ROOT/mace/cli/run_train.py" \
  --name=AtomicDipolesMACE-toy \
  --model=AtomicDipolesMACE --loss=dipole --error_table=DipoleRMSE \
  --train_file="$DATA/atomicdipoles_water_train.extxyz" \
  --valid_file="$DATA/atomicdipoles_water_valid.extxyz" --valid_fraction=0 \
  --E0s="{1: 0.0, 8: 0.0}" \
  --dipole_key=REF_dipoles --dipole_weight=1 \
  --compute_atomic_dipole=True --num_channels=32 --max_L=1 --r_max=4.5 \
  --batch_size="${BATCH_SIZE:-8}" --valid_batch_size=8 \
  --max_num_epochs="${EPOCHS:-100}" --eval_interval=10 --default_dtype=float64 \
  --device="${DEVICE:-cpu}" --seed=21 \
  --model_dir="$OUT" --checkpoints_dir="$OUT" --log_dir="$OUT" \
  --results_dir="$OUT" --work_dir="$OUT"
