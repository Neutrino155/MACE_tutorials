#!/usr/bin/env bash
# Shared paths and dependency setup for the extension training scripts.
set -euo pipefail
export PYTHONWARNINGS="ignore::UserWarning,ignore::DeprecationWarning"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DATA="$ROOT/MACE_extensions/data"
PYTHON="${PYTHON:-python}"
DEFAULT_SOURCE="$ROOT/../mace-field-develop"
if [[ ! -f "$DEFAULT_SOURCE/mace/cli/run_train.py" ]]; then
  DEFAULT_SOURCE="$ROOT/../mace-field"
fi
if [[ "$(basename "$0")" == "train_magnetic.sh" && -z "${MACEFIELD_ROOT:-}" ]]; then
  MAGNETIC_SOURCE="$ROOT/../mace-field"
  if [[ -f "$MAGNETIC_SOURCE/mace/modules/extensions.py" ]] && \
     grep -q 'class MagneticScaleShiftMACE' "$MAGNETIC_SOURCE/mace/modules/extensions.py"; then
    DEFAULT_SOURCE="$MAGNETIC_SOURCE"
  fi
fi
SOURCE_ROOT="${MACEFIELD_ROOT:-$DEFAULT_SOURCE}"
if [[ ! -f "$SOURCE_ROOT/mace/cli/run_train.py" ]]; then
  echo "Set MACEFIELD_ROOT to a MACE-Field checkout from origin/develop containing mace/cli/run_train.py." >&2
  exit 2
fi
export PYTHONPATH="$SOURCE_ROOT${PYTHONPATH:+:$PYTHONPATH}"
