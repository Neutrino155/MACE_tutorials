#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/common.sh"
"$PYTHON" "$ROOT/MACE_extensions/scripts/bootstrap.py" --feature="base"
OUT="${OUT_DIR:-$ROOT/MACE_extensions/models/macefield}"
mkdir -p "$OUT"
INITIAL_MODEL_ARGS=()
if [[ -n "${INITIAL_MODEL:-}" ]]; then
  # Optional fine-tuning continues from an existing single-head toy model.
  INITIAL_MODEL_ARGS+=("--foundation_model=$INITIAL_MODEL" "--multiheads_finetuning=False")
fi
RESPONSE_ARGS=(--compute_polarization=False --compute_becs=False --compute_polarizability=False)
if [[ "${COMPUTE_RESPONSES:-0}" == "1" ]]; then
  RESPONSE_ARGS=(--compute_polarization=True --compute_becs=True --compute_polarizability=True)
fi
"$PYTHON" -W ignore::UserWarning -W ignore::DeprecationWarning \
  "$ROOT/MACE_extensions/scripts/run_macefield_cli.py" \
  "$SOURCE_ROOT/mace/cli/run_train.py" \
  --name=MACEField-Landau --model=MACEField --loss=universal_field \
  --hidden_irreps="${HIDDEN_IRREPS:-16x0e + 16x1o}" --num_interactions=2 --r_max=5.0 \
  --train_file="$DATA/macefield_batio3_toy_train.extxyz" \
  --valid_file="$DATA/macefield_batio3_toy_valid.extxyz" --valid_fraction=0 \
  --energy_key=REF_energy --forces_key=REF_forces \
  --electric_field_key=REF_electric_field --polarization_key=REF_polarization \
  --becs_key=REF_becs --polarizability_key=REF_polarizability \
  --compute_forces=True --compute_stress=False "${RESPONSE_ARGS[@]}" \
  --energy_weight="${ENERGY_WEIGHT:-1}" --forces_weight="${FORCES_WEIGHT:-100}" \
  --polarization_weight="${POLARIZATION_WEIGHT:-0}" --becs_weight="${BECS_WEIGHT:-0}" \
  --polarizability_weight="${POLARIZABILITY_WEIGHT:-0}" --stress_weight=0 \
  --polarizability_loss_mode="${POLARIZABILITY_LOSS_MODE:-standardized_symmetric_huber}" \
  --huber_delta="${HUBER_DELTA:-0.5}" \
  --E0s="{8: 0.0, 22: 0.0, 56: 0.0}" \
  --batch_size="${BATCH_SIZE:-32}" --valid_batch_size=32 \
  --max_num_epochs="${EPOCHS:-160}" --eval_interval=10 --default_dtype=float64 \
  --device="${DEVICE:-${MACE_TUTORIAL_DEVICE:-cpu}}" --seed=23 --lr="${LR:-0.01}" \
  --freeze="${FREEZE:-0}" \
  "${INITIAL_MODEL_ARGS[@]}" \
  --model_dir="$OUT" --checkpoints_dir="$OUT" --log_dir="$OUT" \
  --results_dir="$OUT" --work_dir="$OUT"
