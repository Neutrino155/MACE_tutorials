#!/usr/bin/env bash
# Shared paths and dependency setup for the extension training scripts.
set -euo pipefail
export PYTHONWARNINGS="ignore::UserWarning,ignore::DeprecationWarning"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DATA="$ROOT/MACE_extensions/data"
PYTHON="${PYTHON:-python}"
SOURCE_FEATURE="${SOURCE_FEATURE:-field}"
case "$SOURCE_FEATURE" in
  field)
    SOURCE_ROOT="${MACEFIELD_ROOT:-$ROOT/../mace-field-develop}"
    if [[ ! -d "$SOURCE_ROOT" && -z "${MACEFIELD_ROOT:-}" ]]; then
      SOURCE_ROOT="$ROOT/../mace-field"
    fi
    export MACEFIELD_ROOT="$SOURCE_ROOT"
    ;;
  upstream|magnetic|les)
    SOURCE_ROOT="${MACE_ROOT:-$ROOT/../mace-upstream-tutorial}"
    if [[ ! -d "$SOURCE_ROOT" && -z "${MACE_ROOT:-}" ]]; then
      SOURCE_ROOT="$ROOT/../mace-upstream-tutorial"
      git clone --depth 1 --branch develop https://github.com/ACEsuit/mace.git "$SOURCE_ROOT"
    fi
    export MACE_ROOT="$SOURCE_ROOT"
    ;;
  *)
    echo "SOURCE_FEATURE must be field, upstream, magnetic, or les." >&2
    exit 2
    ;;
esac
if [[ ! -f "$SOURCE_ROOT/mace/cli/run_train.py" ]]; then
  echo "MACE source checkout not found at $SOURCE_ROOT; set MACEFIELD_ROOT or MACE_ROOT." >&2
  exit 2
fi
export SOURCE_FEATURE SOURCE_ROOT
export PYTHONPATH="$SOURCE_ROOT${PYTHONPATH:+:$PYTHONPATH}"
