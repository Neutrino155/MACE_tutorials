#!/usr/bin/env python3
"""Run the MACE-Field training CLI with warning setup."""
from __future__ import annotations

from pathlib import Path
import runpy
import sys
import warnings

CLI = Path(sys.argv[1]).expanduser().resolve()
if not CLI.is_file():
    raise FileNotFoundError(CLI)
SOURCE_ROOT = CLI.parents[2]
TUTORIAL_ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(TUTORIAL_ROOT), str(SOURCE_ROOT)]

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
_original_showwarning = warnings.showwarning


def _quiet_user_and_deprecation_warnings(
    message, category, filename, lineno, file=None, line=None
):
    if issubclass(category, (UserWarning, DeprecationWarning)):
        return
    _original_showwarning(message, category, filename, lineno, file=file, line=line)


warnings.showwarning = _quiet_user_and_deprecation_warnings

sys.argv = [str(CLI), *sys.argv[2:]]
runpy.run_path(str(CLI), run_name="__main__")
