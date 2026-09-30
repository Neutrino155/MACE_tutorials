#!/usr/bin/env python3
"""Build a small archive containing the MACE extension tutorial assets for Colab."""
from pathlib import Path
import argparse
import zipfile
ROOT = Path(__file__).resolve().parents[2]
ASSET_ROOT = ROOT / "MACE_extensions"
def build(output: Path) -> Path:
    inputs = [p for folder in ("data", "figures") for p in (ASSET_ROOT / folder).rglob("*") if p.is_file()]
    inputs.extend([ASSET_ROOT / "models/pretrained_models.zip"])
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=4) as zf:
        for path in inputs:
            zf.write(path, path.relative_to(ROOT).as_posix())
    print(f"Wrote {output} ({output.stat().st_size / 1e6:.2f} MB)")
    return output
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ASSET_ROOT / "mace_extensions_assets.zip")
    args=parser.parse_args()
    build(args.output.resolve())
if __name__ == "__main__": main()
