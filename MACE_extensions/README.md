# MACE extension notebooks

These notebooks demonstrate four different changes around the MACE architecture. T00 gives a code-level recipe using MACEField as its example; T01–T04 then show field-conditioned response, dipole readout, magnetic inputs and long-range electrostatics. They are intended as a short closing demonstration after Practice I and II.

## Source code used

The notebooks select the implementation that contains the model being taught:

| Notebook | Source |
|---|---|
| T00 and T01 · MACEField | [MACE-Field](https://github.com/mdi-group/mace-field), `develop` |
| T02 · AtomicDipolesMACE | [ACEsuit/MACE](https://github.com/ACEsuit/mace), `develop` |
| T03 · Magnetic MACE | [ACEsuit/MACE](https://github.com/ACEsuit/mace), `develop` |
| T04 · MACELES | [ACEsuit/MACE](https://github.com/ACEsuit/mace), `develop` |

Open the notebook from this repository in Jupyter or use its Colab badge. Setup cells locate or clone the appropriate source checkout. Local notebooks accept `MACEFIELD_ROOT` for MACEField and `MACE_ROOT` for upstream MACE; if neither is set, setup looks beside this repository and clones the required checkout if needed. Restart the kernel when switching between MACE implementations in the same environment.

T03 needs the upstream `magnetic` dependencies (`sphericart-torch` and `torch-geometric`). T04 needs the pinned LES dependency listed in the MACE checkout's `requirements/les.txt`. The setup cells install optional dependencies when they are missing.

The matching command-line training scripts are in [`scripts/`](scripts/): `train_macefield.sh` selects MACE-Field, while the AtomicDipoles, magnetic, LES, and short-range-control scripts select ACEsuit/MACE. Set `MACE_ROOT` to choose the upstream checkout or `MACEFIELD_ROOT` for MACE-Field. Each script writes its trained model and logs beneath `MACE_extensions/models/` by default; set `OUT_DIR` to change that location.

## Teaching data

The deterministic example datasets live in [`data/`](data/README.md) and can be regenerated from the repository root with:

```bash
python MACE_extensions/scripts/prepare_teaching_data.py
```

The water dipole files include energy, force and dipole labels. T02 deliberately trains `AtomicDipolesMACE` against the dipole-only loss, because that model class does not predict energy or forces; the extra labels can be used with `EnergyDipolesMACE`. The water-dimer LES files already include energy and force labels in both splits, and T04 checks their presence before training.

All generated labels are analytic teaching targets, not DFT or experimental data. See the data guide for units, label definitions, the MACEField toy's response surface and its scope limits.
