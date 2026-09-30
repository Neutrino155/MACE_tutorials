#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
"$PYTHON" "$ROOT/MACE_extensions/scripts/bootstrap.py" --feature="base,les"
OUT="${OUT_DIR:-$ROOT/MACE_extensions/models/maceles}"
mkdir -p "$OUT"
"$PYTHON" "$SOURCE_ROOT/mace/cli/run_train.py" \
  --name=MACELES-toy --model=MACELES --loss=weighted \
  --hidden_irreps="32x0e + 32x1o + 32x2e" --num_interactions=2 --r_max=5.0 \
  --train_file="$DATA/maceles_water_dimer_train.extxyz" \
  --valid_file="$DATA/maceles_water_dimer_valid.extxyz" --valid_fraction=0 \
  --E0s="{1: 0.0, 8: 0.0}" \
  --energy_key=REF_energy --forces_key=REF_forces \
  --les_arguments="$ROOT/MACE_extensions/config/maceles_toy.yaml" \
  --energy_weight=1 --forces_weight=10 --stress_weight=0 \
  --batch_size="${BATCH_SIZE:-8}" --valid_batch_size=8 \
  --max_num_epochs="${EPOCHS:-100}" --eval_interval=10 --default_dtype=float64 \
  --device="${DEVICE:-cpu}" --seed=24 \
  --model_dir="$OUT" --checkpoints_dir="$OUT" --log_dir="$OUT" \
  --results_dir="$OUT" --work_dir="$OUT"
