# MACE_tutorials

Written for first-year PhD students in computational chemistry, this repository brings together hands-on and advanced notebooks for learning, applying and extending MACE-based machine-learning interatomic potentials. The main workshop route is practical: inspect data, fit and evaluate a model, then improve it through iterative training and active learning. Advanced theory and applications are optional routes for students who want to go further. The MACE extension examples form a short demonstration near the end of the session.

## Choose a notebook route

### Core workshop: work through these in order

1. [**MACE Practice I**](MACE_in_practice_I/T01-MACE-Practice-I.ipynb) — inspect atomistic data, configure and train a MACE model, and evaluate its predictions.
2. [**MACE Practice II**](MACE_in_practice_II/T02-MACE-Practice-II.ipynb) — improve a model using iterative training and active learning, then explore foundation models and fine-tuning.

### Optional: continue into advanced material

Open a notebook from [`MACE_advanced/`](MACE_advanced/) when you are ready for more theory or applications:

| Notebook | Focus |
|---|---|
| [T03 · MACE Theory](MACE_advanced/T03-MACE-Theory.ipynb) | Inspect MACE architecture and code-level operations. |
| [T04 · MLIP applications](MACE_advanced/T04-MLIP-Apps.ipynb) | Apply MLIPs to lithium diffusion and nudged elastic band workflows. |
| [T05 · Molecular NEB](MACE_advanced/T05-MACE-neb.ipynb) | Explore a molecular reaction pathway with an MLIP. |

### Closing demonstration: examples of extending MACE

[`MACE_extensions/`](MACE_extensions/) contains a short architecture overview followed by focused examples. During the workshop, these form a **30–45 minute demonstration near the end**; the notebooks are also available for later self-study:

| Notebook | Adaptation illustrated |
|---|---|
| [T00 · Extending MACE](MACE_extensions/T00-Extending-MACE.ipynb) | Compare where additional inputs, outputs and physical terms can enter a MACE model. |
| [T01 · MACEField](MACE_extensions/T01-MACEField.ipynb) | Condition energy and response on an external electric field. |
| [T02 · AtomicDipolesMACE](MACE_extensions/T02-AtomicDipolesMACE.ipynb) | Predict an equivariant vector property. |
| [T03 · Magnetic MACE](MACE_extensions/T03-MagneticMACE.ipynb) | Include magnetic moments when predicting energies and forces. |
| [T04 · MACELES](MACE_extensions/T04-MACELES.ipynb) | Add an explicit long-range electrostatic energy contribution. |

## Lennard-Jones Centre summer school

These materials support the Lennard-Jones Centre and Thomas Young Centre Summer School on Atomic-Scale Modelling, held in Cambridge from **28 September to 2 October 2026**. The tutorial session is on **Thursday 1 October, 14:00–17:00**. The core practical notebooks are the focus; students who finish early can choose an advanced notebook, and the extension models are shown in the final segment.

**People involved:** Bradley Martin, Isaac Parker and Joe Hart. The schedule below follows the session allocation of Bradley Martin from 14:00–16:00 and Joe Hart and Isaac Parker from 16:00–17:00.

**Introductory slides:** [MACE in practice — LJC Summer School](https://docs.google.com/presentation/d/1LzDnWMp7qsf1ujuK5L8gjd2XYRywSiGsmZi62YMFEtk/edit)

| Time | Activity |
|---|---|
| 14:00–14:50 | Bradley Martin · MACE Practice I: data, fitting and evaluation |
| 14:50–15:00 | Break · 10 min |
| 15:00–15:50 | Bradley Martin · MACE Practice II: iterative training and active learning |
| 15:50–16:00 | Break · 10 min |
| 16:00–16:15 | Optional advanced notebooks: theory or applications, as time and interest allow |
| 16:15–16:50 | Joe Hart and Isaac Parker · Demonstrations of selected MACE extensions |
| 16:50–17:00 | Break and close · 10 min |

The extension segment will use MACEField as the lead example and compare selected dipole, magnetic and long-range electrostatic adaptations. The full extension notebook set is available in the folder above.

## Notebook credits and provenance

The notebooks in this repository are the workshop materials; use the links above to navigate between them without needing another tutorial collection. The [MACE Theory notebook](MACE_advanced/T03-MACE-Theory.ipynb) credits **Will Baldwin** as its developer and identifies **Ilyes Batatia’s** developer tutorial as its basis. The source notebooks for Practice I, Practice II, and the two advanced application examples do not currently include an individual author statement. This README does not infer authorship where the notebook itself does not state it. Bradley Martin, Isaac Parker and Joe Hart are the people involved in teaching this session.

## Running the notebooks

Open notebooks in Jupyter or use their **Open in Colab** links. You can launch Jupyter from the repository root or the notebook folder; setup cells select the notebook folder and use the datasets included here. Install each notebook's Python dependencies in your local environment before running it. The extension examples include local/Colab setup and training scripts; see [`MACE_extensions/README.md`](MACE_extensions/README.md) and [`MACE_extensions/data/README.md`](MACE_extensions/data/README.md) for their source and data requirements.

The extension datasets are small analytic teaching targets, not DFT or experimental data. The model-specific notebooks explain what each example demonstrates and the limits of its scientific interpretation.
