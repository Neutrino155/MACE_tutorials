"""Interactive JavaScript canvas structure views for the extension notebooks.

The viewer is bundled with this repository and emitted directly as notebook
JavaScript. It has no Plotly or ipywidgets dependency.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
import json
from pathlib import Path
from typing import Any

import numpy as np
from ase import Atoms
from ase.data import atomic_numbers, covalent_radii
from ase.neighborlist import neighbor_list
from IPython.display import Javascript


_LIGAND_ELEMENTS = {"O", "N", "F", "Cl", "Br", "I", "S", "Se", "Te"}
_DISPLAY_RADII = {
    "H": 0.31, "C": 0.76, "N": 0.71, "O": 0.66, "F": 0.57, "P": 1.07,
    "S": 1.05, "Cl": 1.02, "Ba": 2.15, "Ti": 1.6, "Zr": 1.75, "Pb": 1.46,
    "Bi": 1.48, "Fe": 1.32, "Mn": 1.39, "Nb": 1.64, "Ta": 1.7, "W": 1.62,
}
_ELEMENT_COLORS = {
    "H": "#dce5eb", "C": "#354b5e", "N": "#3479a8", "O": "#d95650",
    "F": "#69a865", "P": "#e28b3c", "S": "#d2b34d", "Cl": "#45a581",
    "Ba": "#4b9a72", "Ti": "#8a70bd", "Fe": "#ca7440", "Mn": "#8466a7",
    "Zr": "#64849a", "Pb": "#77717f", "Bi": "#ad7771", "W": "#586d7d",
    "Si": "#e6ae32", "Na": "#7d84c2", "Mg": "#5dba7b", "Al": "#ad8ac7",
    "Ca": "#3f9c77", "Sr": "#4ba886", "Cu": "#b87333", "Zn": "#7895a5",
}
_SCALAR_COLORS = [[0.0, "#3176a1"], [0.5, "#f7f7f5"], [1.0, "#b8473a"]]


def _covalent_radius(symbol: str) -> float:
    number = atomic_numbers.get(symbol, 0)
    if number and number < len(covalent_radii):
        value = float(covalent_radii[number])
        if np.isfinite(value) and value > 0.2:
            return value
    return 0.9


def _coordination_limit(symbol: str) -> int:
    if symbol == "H":
        return 1
    if symbol in {"C", "Si", "Ge"}:
        return 4
    if symbol in {"B", "N", "P", "As", "Sb"}:
        return 6
    if symbol in {"He", "Ne", "Ar", "Kr", "Xe", "Rn", "Og"}:
        return 0
    return 12


def _shell_is_regular(vectors: np.ndarray) -> bool:
    """Keep clearly tetrahedral or octahedral coordination shells."""
    unit_vectors = vectors / np.maximum(np.linalg.norm(vectors, axis=1, keepdims=True), 1e-12)
    dots = [float(np.dot(unit_vectors[i], unit_vectors[j]))
            for i in range(len(unit_vectors)) for j in range(i + 1, len(unit_vectors))]
    if len(vectors) == 4:
        return all(abs(value + 1.0 / 3.0) < 0.48 for value in dots)
    if len(vectors) == 6:
        opposite = sum(value < -0.72 for value in dots)
        transverse = sum(abs(value) < 0.62 for value in dots)
        return opposite == 3 and transverse >= 10
    return False


def _frame_geometry(atoms: Atoms) -> tuple[list[list[float]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Return wrapped display coordinates, periodic bonds and compact cages."""
    visual = atoms.copy()
    pbc = np.asarray(visual.pbc, dtype=bool)
    cell = np.asarray(visual.cell.array, dtype=float)
    if pbc.any():
        scaled = visual.get_scaled_positions(wrap=False)
        for axis, periodic in enumerate(pbc):
            if periodic:
                scaled[:, axis] %= 1.0
        visual.set_scaled_positions(scaled)
    positions = np.asarray(visual.positions, dtype=float)
    symbols = visual.get_chemical_symbols()
    bonds: list[dict[str, Any]] = []
    polyhedra: list[dict[str, Any]] = []
    if not len(visual):
        return positions.tolist(), bonds, polyhedra

    pair_i, pair_j, shifts, displacements = neighbor_list("ijSD", visual, 4.2, self_interaction=False)
    distances = np.linalg.norm(displacements, axis=1)
    candidates = []
    for i, j, shift, distance in zip(pair_i, pair_j, shifts, distances):
        i, j = int(i), int(j)
        shift = np.asarray(shift, dtype=int)
        if i > j:
            continue
        if i == j:
            first_nonzero = next((int(value) for value in shift if value), 0)
            if first_nonzero <= 0:
                continue
        radius_sum = _covalent_radius(symbols[i]) + _covalent_radius(symbols[j])
        cutoff = min(3.55, 1.24 * radius_sum + 0.12)
        distance = float(distance)
        ratio = distance / max(radius_sum, 1e-12)
        if distance < 0.45 or distance > cutoff or ratio > 1.30:
            continue
        candidates.append((ratio, distance, i, j, shift))
    candidates.sort(key=lambda item: (item[0], item[1]))
    coordination = np.zeros(len(visual), dtype=int)
    for ratio, _distance, i, j, shift in candidates:
        self_image = i == j
        i_cost = 2 if self_image else 1
        if _coordination_limit(symbols[i]) == 0 or _coordination_limit(symbols[j]) == 0:
            continue
        if coordination[i] + i_cost > _coordination_limit(symbols[i]):
            continue
        if not self_image and coordination[j] + 1 > _coordination_limit(symbols[j]):
            continue
        coordination[i] += i_cost
        if not self_image:
            coordination[j] += 1
        bonds.append({"i": i, "j": j, "shift": shift.astype(int).tolist(), "ratio": float(ratio)})

    for center, symbol in enumerate(symbols):
        if symbol == "H" or symbol in _LIGAND_ELEMENTS:
            continue
        shell_candidates = []
        for i, j, shift, distance in zip(pair_i, pair_j, shifts, distances):
            if int(i) != center or symbols[int(j)] not in _LIGAND_ELEMENTS:
                continue
            maximum = 1.28 * (
                _DISPLAY_RADII.get(symbol, 1.0) + _DISPLAY_RADII.get(symbols[int(j)], 0.9)
            ) + 0.1
            distance = float(distance)
            if 0.45 < distance <= maximum:
                shift = np.asarray(shift, dtype=int)
                vector = positions[int(j)] + shift @ cell - positions[center]
                shell_candidates.append((distance, int(j), shift, vector))
        shell_candidates.sort(key=lambda item: item[0])
        shell_size = min(7, len(shell_candidates))
        for index in range(3, min(shell_size, 7)):
            previous, following = shell_candidates[index - 1][0], shell_candidates[index][0]
            if following - previous > max(0.35, previous * 0.16):
                shell_size = index
                break
        shell = shell_candidates[:shell_size]
        vectors = np.asarray([item[3] for item in shell], dtype=float)
        if len(vectors) not in {4, 6} or not _shell_is_regular(vectors):
            continue
        polyhedra.append({
            "center": symbol,
            "origin": positions[center].tolist(),
            "vectors": vectors.tolist(),
            "images": [
                {
                    "position": (positions[item[1]] + item[2] @ cell).tolist(),
                    "symbol": symbols[item[1]],
                    "periodic": bool(np.any(item[2])),
                }
                for item in shell
            ],
        })
    return positions.tolist(), bonds, polyhedra


def _vector_parts(vector: dict | Sequence, atoms: Atoms) -> dict[str, Any]:
    if isinstance(vector, dict):
        origin = vector.get("origin", atoms.get_center_of_mass())
        direction = vector["vector"]
        label = vector.get("label", "Vector")
        color = vector.get("color", "#147d9b")
        units = vector.get("units", "")
        length = vector.get("length", 1.45)
    else:
        if len(vector) == 5:
            origin, direction, label, color, units = vector
            length = 1.45
        else:
            origin, direction, label, color, units, length = vector
    return {
        "origin": np.asarray(origin, dtype=float).reshape(3).tolist(),
        "vector": np.asarray(direction, dtype=float).reshape(3).tolist(),
        "label": str(label), "color": str(color), "units": str(units), "length": float(length),
    }


def _safe_values(values: Sequence[float] | None, atom_count: int) -> list[float] | None:
    if values is None:
        return None
    result = np.asarray(values, dtype=float).reshape(-1)
    if len(result) != atom_count:
        raise ValueError("atom_values must contain one value per atom")
    if not np.all(np.isfinite(result)):
        raise ValueError("atom_values must be finite")
    return result.tolist()


def _viewer_output(payload: dict[str, Any], *, gallery: bool = False) -> Javascript:
    source_path = Path(__file__).with_name("structure_viewer.js")
    source = source_path.read_text(encoding="utf-8")
    data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    data = data.replace("</", "<\\/")
    entrypoint = "createMaceStructureGallery" if gallery else "createMaceStructureViewer"
    script = (
        "(function(){\n"
        # Colab's window.element can be detached, so create a connected mount
        # in the output frame. Jupyter supplies the output node as `element`.
        "const isColab = Boolean(window.google && window.google.colab);\n"
        "const jupyterElement = typeof element !== 'undefined' ? element : null;\n"
        "const candidates = isColab\n"
        "  ? [(() => {\n"
        "      const mount = document.createElement(\"div\");\n"
        "      (document.body || document.documentElement).appendChild(mount);\n"
        "      return mount;\n"
        "    })()]\n"
        "  : [jupyterElement, window.element];\n"
        "const host = candidates.map((candidate) => candidate && typeof candidate.appendChild === 'function' ? candidate : "
        "(candidate && candidate[0] && typeof candidate[0].appendChild === 'function' ? candidate[0] : null)).find(Boolean);\n"
        "if (!host || !host.appendChild) throw new Error('Structure viewer could not find this cell output element.');\n"
        "const spec=" + data + ";\n"
        + source
        + "\ntry {\n"
        + "  " + entrypoint + "(host,spec);\n"
        # Colab runs each output in a sandboxed iframe. Resize it after
        # adding the canvas so it is not clipped to the initial output height.
        + "  const colabOutput = isColab ? window.google.colab.output : null;\n"
        + "  if (colabOutput && typeof colabOutput.setIframeHeight === 'function') {\n"
        + "    const resizeOutput = () => { try { colabOutput.setIframeHeight(Math.max(document.documentElement.scrollHeight, document.body ? document.body.scrollHeight : 0), true, {maxHeight: 1200}); } catch (resizeError) { console.warn('Could not resize Colab structure viewer output', resizeError); } };\n"
        + "    requestAnimationFrame(resizeOutput);\n"
        + "    setTimeout(resizeOutput, 100);\n"
        + "  }\n"
        + "} catch (error) {\n"
        "  const message = document.createElement('div');\n"
        "  message.style.cssText = 'padding:12px;border:1px solid #d98b8b;border-radius:8px;background:#fff5f5;color:#8b2020;font:13px system-ui,sans-serif';\n"
        "  message.textContent = 'Interactive structure viewer failed: ' + (error && error.message ? error.message : String(error));\n"
        "  (host.shadowRoot || host).replaceChildren(message);\n"
        "  console.error('Interactive structure viewer failed', error);\n"
        "}\n})();"
    )
    return Javascript(script)


def _scene_payload(
    structures: Sequence[Atoms],
    *,
    title: str,
    atom_values: Sequence[Sequence[float] | None] | None = None,
    scalar_name: str = "Value",
    scalar_units: str = "",
    vectors_by_frame: Sequence[Iterable[dict | Sequence]] | None = None,
    frame_labels: Sequence[str] | None = None,
    show_cell: bool | None = None,
    height: int = 520,
    play_speed: int = 180,
) -> dict[str, Any]:
    structures = list(structures)
    if not structures:
        raise ValueError("At least one structure is required")
    symbols = structures[0].get_chemical_symbols()
    if any(atoms.get_chemical_symbols() != symbols for atoms in structures):
        raise ValueError("Animated structures must keep the same atom order and species")
    count = len(structures)
    if atom_values is None:
        atom_values = [None] * count
    if vectors_by_frame is None:
        vectors_by_frame = [()] * count
    if frame_labels is None:
        frame_labels = [f"Frame {index + 1}" for index in range(count)]
    if not (len(atom_values) == len(vectors_by_frame) == len(frame_labels) == count):
        raise ValueError("Frame labels, scalar values and vectors must match the structures")

    frames = []
    for index, atoms in enumerate(structures):
        positions, bonds, polyhedra = _frame_geometry(atoms)
        frames.append({
            "symbols": atoms.get_chemical_symbols(),
            "positions": positions,
            "cell": np.asarray(atoms.cell.array, dtype=float).tolist(),
            "pbc": np.asarray(atoms.pbc, dtype=bool).tolist(),
            "bonds": bonds,
            "polyhedra": polyhedra,
            "values": _safe_values(atom_values[index], len(atoms)),
            "vectors": [_vector_parts(vector, atoms) for vector in vectors_by_frame[index]],
        })
    if show_cell is None:
        show_cell = bool(np.any(structures[0].pbc))
    return {
        "title": str(title),
        "height": int(height),
        "playSpeed": int(play_speed),
        "frameLabels": [str(label) for label in frame_labels],
        "scalarName": str(scalar_name),
        "scalarUnits": str(scalar_units),
        "showCell": bool(show_cell),
        "frames": frames,
    }


def _render(
    structures: Sequence[Atoms],
    *,
    title: str,
    atom_values: Sequence[Sequence[float] | None] | None = None,
    scalar_name: str = "Value",
    scalar_units: str = "",
    vectors_by_frame: Sequence[Iterable[dict | Sequence]] | None = None,
    frame_labels: Sequence[str] | None = None,
    show_cell: bool | None = None,
    height: int = 520,
    play_speed: int = 180,
) -> Javascript:
    return _viewer_output(_scene_payload(
        structures, title=title, atom_values=atom_values, scalar_name=scalar_name,
        scalar_units=scalar_units, vectors_by_frame=vectors_by_frame,
        frame_labels=frame_labels, show_cell=show_cell, height=height,
        play_speed=play_speed,
    ))


def show_structure_gallery(
    structures: Mapping[str, Atoms],
    *,
    title: str = "Explore example structures",
    default_choice: str | None = None,
    height: int = 500,
) -> Javascript:
    """Return one JavaScript-backed gallery for structures with different species."""
    choices = [(str(name), atoms) for name, atoms in structures.items()]
    if not choices:
        raise ValueError("At least one named structure is required")
    names = [name for name, _atoms in choices]
    if len(set(names)) != len(names):
        raise ValueError("Structure gallery names must be unique")
    selected = str(default_choice) if default_choice is not None else names[0]
    if selected not in names:
        raise ValueError(f"default_choice {selected!r} is not one of {names!r}")
    payload = {
        "title": str(title),
        "choices": [
            {
                "name": name,
                "scene": _scene_payload([atoms], title=name, height=height),
            }
            for name, atoms in choices
        ],
        "defaultChoice": selected,
    }
    return _viewer_output(payload, gallery=True)


def show_structure(
    atoms: Atoms,
    *,
    title: str = "Structure",
    atom_values: Sequence[float] | None = None,
    scalar_name: str = "Atomic value",
    scalar_units: str = "",
    vectors: Iterable[dict | Sequence] = (),
    values: Sequence[float] | None = None,
    value_name: str | None = None,
    value_units: str | None = None,
    show_cell: bool | None = None,
    height: int = 520,
) -> Javascript:
    """Return an interactive canvas view of one ASE structure."""
    if atom_values is None:
        atom_values = values
    if value_name is not None:
        scalar_name = value_name
    if value_units is not None:
        scalar_units = value_units
    return _render(
        [atoms], title=title, atom_values=[atom_values], scalar_name=scalar_name,
        scalar_units=scalar_units, vectors_by_frame=[vectors],
        show_cell=show_cell, height=height,
    )


def animate_structures(
    structures: Sequence[Atoms],
    *,
    title: str = "Structure trajectory",
    frame_labels: Sequence[str] | None = None,
    atom_values: Sequence[Sequence[float] | None] | None = None,
    scalar_name: str = "Value",
    scalar_units: str = "",
    vectors_by_frame: Sequence[Iterable[dict | Sequence]] | None = None,
    show_cell: bool | None = None,
    height: int = 560,
    play_speed: int = 180,
) -> Javascript:
    """Return an interactive frame slider and playback view for ASE structures."""
    return _render(
        structures, title=title, frame_labels=frame_labels, atom_values=atom_values,
        scalar_name=scalar_name, scalar_units=scalar_units,
        vectors_by_frame=vectors_by_frame, show_cell=show_cell, height=height,
        play_speed=play_speed,
    )


def show_vector_structure(
    atoms: Atoms,
    vector: Sequence[float],
    *,
    label: str = "Vector",
    units: str = "",
    color: str = "#d78b20",
    length: float = 1.5,
    title: str = "Structure with vector",
    origin: Sequence[float] | None = None,
    height: int = 520,
) -> Javascript:
    """Show a visually scaled vector while retaining its physical magnitude."""
    overlay = {
        "vector": vector, "label": label, "units": units,
        "color": color, "length": length,
    }
    if origin is not None:
        overlay["origin"] = origin
    return show_structure(atoms, title=title, vectors=[overlay], height=height)
