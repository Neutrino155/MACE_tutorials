// Notebook-focused canvas adaptation of the interaction style in Bradley
// Martin's MP Ferroelectrics explorer:
// https://github.com/Neutrino155/Neutrino155.github.io/tree/main/public/mp-ferroelectrics/explorer
function createMaceStructureViewer(host, spec) {
  const root = host.shadowRoot || (host.attachShadow ? host.attachShadow({ mode: "open" }) : host);
  const style = document.createElement("style");
  style.textContent = [
    ":host{display:block;font-family:Inter,ui-sans-serif,system-ui,sans-serif;color:#20394b}",
    ".mace-view{--height:520px;background:#fff;border:1px solid #d9e3e9;border-radius:12px;box-shadow:0 3px 14px #18364b0c;overflow:hidden}",
    ".head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;padding:14px 16px 10px;background:#f8fafb}",
    ".title{margin:0;color:#183c50;font-size:16px;font-weight:750;line-height:1.25}",
    ".hint{margin:5px 0 0;color:#718494;font-size:11px}",
    ".toolbar{display:flex;align-items:center;flex-wrap:wrap;gap:7px 12px;padding:9px 12px;border-top:1px solid #e5ebef;border-bottom:1px solid #e5ebef;background:#fff}",
    ".toolbar button,.toolbar select{padding:5px 8px;border:1px solid #cbd8e0;border-radius:7px;background:#fff;color:#29495e;font:inherit;font-size:11px;font-weight:650;cursor:pointer}",
    ".toolbar button:hover{background:#f2f7f8}.toolbar button.active{background:#1d6570;border-color:#1d6570;color:#fff}",
    ".toolbar label{display:flex;align-items:center;gap:5px;color:#526b7b;font-size:11px;font-weight:600;white-space:nowrap}",
    ".toolbar input[type=range]{width:88px;accent-color:#238178}.toolbar input[type=checkbox]{accent-color:#238178}",
    ".toolbar output{min-width:35px;color:#496274;font-size:10px;font-variant-numeric:tabular-nums}",
    ".stage{position:relative;height:var(--height);min-height:300px;background:radial-gradient(ellipse at 50% 42%,#fff 0,#f7fafb 68%,#eff4f6 100%);overflow:hidden}",
    "canvas{display:block;width:100%;height:100%;touch-action:none;cursor:grab}canvas:active{cursor:grabbing}",
    ".caption{position:absolute;left:12px;bottom:10px;max-width:78%;padding:5px 8px;border:1px solid #dce5ea;border-radius:6px;background:#ffffffd9;color:#526a7b;font-size:10px;pointer-events:none}",
    ".footer{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;padding:9px 13px;border-top:1px solid #e7edf0;background:#fbfcfd}",
    ".legend{display:flex;align-items:center;gap:5px 9px;flex-wrap:wrap}.legend-item{display:inline-flex;align-items:center;gap:4px;color:#526b7b;font-size:10px}",
    ".swatch{width:10px;height:10px;border:1px solid #ffffff;border-radius:50%;box-shadow:0 0 0 1px #aab9c2}",
    ".valuebar{width:74px;height:8px;border:1px solid #d3dde3;border-radius:5px;background:linear-gradient(90deg,#3176a1,#f7f7f7,#b8473a)}",
    ".detail{margin-left:auto;color:#526b7b;text-align:right;font-size:10px;font-variant-numeric:tabular-nums}",
    ".detail strong{color:#28485c}.error{padding:14px;color:#9b263d;font-size:12px}",
    "@media(max-width:600px){.head{padding:11px}.toolbar{gap:7px}.stage{height:390px}.detail{width:100%;text-align:left;margin:0}}",
  ].join("");

  function make(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  }
  const shell = make("div", "mace-view");
  shell.style.setProperty("--height", Math.max(320, Number(spec.height) || 520) + "px");
  const header = make("div", "head");
  const heading = make("div");
  heading.append(make("h3", "title", spec.title || "Atomic structure"));
  heading.append(make("p", "hint", "Drag to rotate freely · Alt-drag to roll · Shift-drag to pan · XYZ inset shows view axes · scroll or pinch to zoom · click an atom for details"));
  header.append(heading);

  const toolbar = make("div", "toolbar");
  const modeButtons = {};
  const periodic = spec.frames.some((frame) => frame.pbc.some(Boolean));
  const defaultShowBonds = spec.showBonds === undefined ? !periodic : Boolean(spec.showBonds);
  const defaultShowLabels = spec.showLabels !== false;
  [["3d", "3D"], ["ab", "ab"], ["bc", "bc"], ["ca", "ca"]].forEach(([mode, label]) => {
    if (mode !== "3d" && !periodic) return;
    const button = make("button", mode === "3d" ? "active" : "", label);
    button.type = "button";
    button.title = mode === "3d" ? "Perspective view" : "View the " + mode + " lattice face";
    button.addEventListener("click", () => {
      state.view = mode;
      if (mode !== "3d") state.planeRotation = 0;
      Object.entries(modeButtons).forEach(([key, item]) => item.classList.toggle("active", key === mode));
      state.pan = { x: 0, y: 0 };
      draw();
    });
    modeButtons[mode] = button;
    toolbar.append(button);
  });

  const playButton = make("button", "", spec.frames.length > 1 ? "Play" : "Reset view");
  playButton.type = "button";
  toolbar.append(playButton);
  const frameLabel = make("output", "", "");
  if (spec.frames.length > 1) {
    const frameControl = make("label", "", "Frame");
    const frameSlider = document.createElement("input");
    frameSlider.type = "range";
    frameSlider.min = "0";
    frameSlider.max = String(spec.frames.length - 1);
    frameSlider.step = "1";
    frameSlider.value = "0";
    frameControl.append(frameSlider, frameLabel);
    toolbar.append(frameControl);
    frameSlider.addEventListener("input", () => {
      state.frame = Number(frameSlider.value);
      draw();
    });
    playButton.addEventListener("click", () => {
      if (state.timer) {
        clearInterval(state.timer);
        state.timer = null;
        playButton.textContent = "Play";
      } else {
        playButton.textContent = "Pause";
        state.timer = setInterval(() => {
          state.frame = (state.frame + 1) % spec.frames.length;
          frameSlider.value = String(state.frame);
          draw();
        }, Math.max(80, Number(spec.playSpeed) || 180));
      }
    });
  } else {
    playButton.addEventListener("click", () => {
      state.rotation = initialRotation(); state.planeRotation = 0; state.zoom = 1; state.pan = { x: 0, y: 0 };
      draw();
    });
  }

  const addToggle = (labelText, key, initial, visible = true) => {
    if (!visible) return null;
    const label = make("label", "", labelText);
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = initial;
    input.addEventListener("change", () => { state[key] = input.checked; draw(); });
    label.prepend(input);
    toolbar.append(label);
    return input;
  };
  addToggle("cell", "showCell", spec.showCell, periodic);
  addToggle("bonds", "showBonds", defaultShowBonds);
  addToggle("polyhedra", "showPolyhedra", true);
  addToggle("labels", "showLabels", defaultShowLabels);

  const sizeLabel = make("label", "", "Atom size");
  const sizeSlider = document.createElement("input");
  sizeSlider.type = "range";
  sizeSlider.min = "0.8"; sizeSlider.max = "2.4"; sizeSlider.step = "0.05"; sizeSlider.value = "1.35";
  const sizeOutput = make("output", "", "1.35×");
  sizeLabel.append(sizeSlider, sizeOutput);
  toolbar.append(sizeLabel);
  sizeSlider.addEventListener("input", () => {
    state.atomScale = Number(sizeSlider.value);
    sizeOutput.textContent = state.atomScale.toFixed(2) + "×";
    draw();
  });

  const stage = make("div", "stage");
  const canvas = document.createElement("canvas");
  stage.append(canvas);
  const caption = make("div", "caption", "");
  stage.append(caption);
  const footer = make("div", "footer");
  const legend = make("div", "legend");
  const detail = make("div", "detail", "");
  footer.append(legend, detail);
  shell.append(header, toolbar, stage, footer);
  root.replaceChildren(style, shell);

  const context = canvas.getContext("2d");
  const state = {
    frame: 0, view: "3d", rotation: initialRotation(), planeRotation: 0, zoom: 1, pan: { x: 0, y: 0 },
    atomScale: 1.35, showCell: Boolean(spec.showCell), showBonds: defaultShowBonds,
    showPolyhedra: true, showLabels: defaultShowLabels, selectedAtom: -1, timer: null,
    pointer: null, hoverAtom: -1,
  };
  const elementColors = {
    H: "#e4ebf0", C: "#354b5e", N: "#3479a8", O: "#d95650", F: "#69a865",
    P: "#e28b3c", S: "#d2b34d", Cl: "#45a581", Ba: "#4b9a72", Ti: "#8a70bd",
    Fe: "#ca7440", Mn: "#8466a7", Zr: "#64849a", Pb: "#77717f", Bi: "#ad7771",
    W: "#586d7d", Si: "#e6ae32", Na: "#7d84c2", Mg: "#5dba7b", Al: "#ad8ac7",
    Ca: "#3f9c77", Sr: "#4ba886", Cu: "#b87333", Zn: "#7895a5",
  };
  const displayRadii = { H: 0.31, C: 0.76, N: 0.71, O: 0.66, F: 0.57, P: 1.07, S: 1.05,
    Cl: 1.02, Ba: 2.15, Ti: 1.6, Zr: 1.75, Pb: 1.46, Bi: 1.48, Fe: 1.32, Mn: 1.39 };
  const uniqueSymbols = [...new Set(spec.frames[0].symbols)];
  const valueRange = (() => {
    const values = spec.frames.flatMap((frame) => frame.values || []).filter(Number.isFinite);
    if (!values.length) return null;
    const bound = Math.max(...values.map((value) => Math.abs(value)), 1e-12);
    return [-bound, bound];
  })();

  function colorFor(symbol) {
    if (elementColors[symbol]) return elementColors[symbol];
    let number = 1;
    for (let i = 0; i < symbol.length; i += 1) number += symbol.charCodeAt(i) * (i + 1);
    return "hsl(" + ((number * 137.508) % 360).toFixed(1) + " 58% 55%)";
  }
  function scalarColor(value) {
    if (!Number.isFinite(value) || !valueRange) return "#8295a3";
    const t = Math.max(0, Math.min(1, (value / valueRange[1] + 1) / 2));
    const stops = [[49, 118, 161], [247, 247, 247], [184, 71, 58]];
    const left = t <= 0.5 ? stops[0] : stops[1];
    const right = t <= 0.5 ? stops[1] : stops[2];
    const mix = t <= 0.5 ? t * 2 : (t - 0.5) * 2;
    return "rgb(" + left.map((value, index) => Math.round(value + mix * (right[index] - value))).join(",") + ")";
  }
  function norm(vector) { return Math.hypot(vector[0], vector[1], vector[2]); }
  function dot(a, b) { return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]; }
  function cross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
  function unit(vector) { const length = norm(vector); return length > 1e-12 ? vector.map((v) => v / length) : [1, 0, 0]; }
  function quaternionMultiply(a, b) {
    return [
      a[0] * b[0] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3],
      a[0] * b[1] + a[1] * b[0] + a[2] * b[3] - a[3] * b[2],
      a[0] * b[2] - a[1] * b[3] + a[2] * b[0] + a[3] * b[1],
      a[0] * b[3] + a[1] * b[2] - a[2] * b[1] + a[3] * b[0],
    ];
  }
  function normalizeQuaternion(quaternion) {
    const length = Math.hypot(...quaternion);
    return quaternion.map((value) => value / (length || 1));
  }
  function initialRotation() {
    const yaw = 0.72 / 2, pitch = -0.42 / 2;
    const aroundZ = [Math.cos(yaw), 0, 0, Math.sin(yaw)];
    const aroundX = [Math.cos(pitch), Math.sin(pitch), 0, 0];
    return normalizeQuaternion(quaternionMultiply(aroundX, aroundZ));
  }
  function rotateVector(vector, quaternion) {
    const imaginary = quaternion.slice(1);
    const firstCross = cross(imaginary, vector);
    const secondCross = cross(imaginary, firstCross);
    return vector.map((value, axis) => value + 2 * (quaternion[0] * firstCross[axis] + secondCross[axis]));
  }
  function trackballPoint(clientX, clientY) {
    const bounds = canvas.getBoundingClientRect();
    const diameter = Math.max(1, Math.min(bounds.width, bounds.height));
    let x = (2 * (clientX - (bounds.left + bounds.width / 2))) / diameter;
    let y = (2 * ((bounds.top + bounds.height / 2) - clientY)) / diameter;
    const radiusSquared = x * x + y * y;
    if (radiusSquared > 1) {
      const length = Math.sqrt(radiusSquared);
      x /= length; y /= length;
      return [x, y, 0];
    }
    return [x, y, Math.sqrt(1 - radiusSquared)];
  }
  function rotateTrackball(from, to) {
    const cosine = Math.max(-1, Math.min(1, dot(from, to)));
    let delta = [1 + cosine, ...cross(from, to)];
    if (cosine < -0.999999) {
      let axis = cross(from, [1, 0, 0]);
      if (norm(axis) < 1e-8) axis = cross(from, [0, 1, 0]);
      axis = unit(axis);
      delta = [0, ...axis];
    }
    state.rotation = normalizeQuaternion(quaternionMultiply(normalizeQuaternion(delta), state.rotation));
  }
  function cart(fractional, cell) {
    return [0, 1, 2].map((axis) => fractional.reduce((sum, value, vector) => sum + value * cell[vector][axis], 0));
  }
  function inverse3(a) {
    const d = a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
      - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
      + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]);
    if (Math.abs(d) < 1e-12) return null;
    return [
      [(a[1][1] * a[2][2] - a[1][2] * a[2][1]) / d, (a[0][2] * a[2][1] - a[0][1] * a[2][2]) / d, (a[0][1] * a[1][2] - a[0][2] * a[1][1]) / d],
      [(a[1][2] * a[2][0] - a[1][0] * a[2][2]) / d, (a[0][0] * a[2][2] - a[0][2] * a[2][0]) / d, (a[0][2] * a[1][0] - a[0][0] * a[1][2]) / d],
      [(a[1][0] * a[2][1] - a[1][1] * a[2][0]) / d, (a[0][1] * a[2][0] - a[0][0] * a[2][1]) / d, (a[0][0] * a[1][1] - a[0][1] * a[1][0]) / d],
    ];
  }
  function currentFrame() { return spec.frames[state.frame]; }
  function centerOf(frame) {
    if (frame.pbc.some(Boolean)) return cart([0.5, 0.5, 0.5], frame.cell);
    const low = [0, 1, 2].map((axis) => Math.min(...frame.positions.map((point) => point[axis])));
    const high = [0, 1, 2].map((axis) => Math.max(...frame.positions.map((point) => point[axis])));
    return low.map((value, axis) => (value + high[axis]) / 2);
  }
  function project(point, frame, width, height) {
    const center = centerOf(frame);
    const vector = point.map((value, axis) => value - center[axis]);
    if (state.view !== "3d") {
      const pairs = { ab: [0, 1], bc: [1, 2], ca: [2, 0] };
      const pair = pairs[state.view] || [0, 1];
      const omitted = [0, 1, 2].find((axis) => axis !== pair[0] && axis !== pair[1]);
      const inv = inverse3(frame.cell);
      if (inv) {
        const frac = [0, 1, 2].map((f) => vector.reduce((sum, value, c) => sum + value * inv[c][f], 0));
        const depth = frac[omitted];
        frac[omitted] = 0;
        const plane = cart(frac, frame.cell);
        const horizontal = unit(frame.cell[pair[0]]);
        const rawVertical = frame.cell[pair[1]];
        const vertical = unit(rawVertical.map((value, axis) => value - dot(rawVertical, horizontal) * horizontal[axis]));
        const hExtent = Math.abs(dot(frame.cell[pair[0]], horizontal)) + Math.abs(dot(frame.cell[pair[1]], horizontal));
        const vExtent = Math.abs(dot(frame.cell[pair[0]], vertical)) + Math.abs(dot(frame.cell[pair[1]], vertical));
        const scale = Math.min(width * 0.76 / Math.max(hExtent, 1e-8), height * 0.72 / Math.max(vExtent, 1e-8)) * state.zoom;
        const angle = state.planeRotation, cosine = Math.cos(angle), sine = Math.sin(angle);
        const planeX = dot(plane, horizontal), planeY = dot(plane, vertical);
        const rotatedX = cosine * planeX - sine * planeY;
        const rotatedY = sine * planeX + cosine * planeY;
        return { x: width / 2 + state.pan.x + rotatedX * scale,
          y: height / 2 + state.pan.y - rotatedY * scale, z: depth, scale };
      }
    }
    const [x, y, z] = rotateVector(vector, state.rotation);
    let extent = Math.max(...frame.cell.map(norm), 0);
    if (!frame.pbc.some(Boolean)) {
      extent = Math.max(...[0, 1, 2].map((axis) =>
        Math.max(...frame.positions.map((p) => p[axis])) - Math.min(...frame.positions.map((p) => p[axis]))), 2.8);
    }
    const scale = Math.min(width, height) * 0.68 / Math.max(extent, 1) * state.zoom;
    return { x: width / 2 + state.pan.x + x * scale, y: height / 2 + state.pan.y - y * scale, z, scale };
  }
  function fitCanvas() {
    const bounds = canvas.getBoundingClientRect();
    const ratio = window.devicePixelRatio || 1;
    canvas.width = Math.max(1, Math.round(bounds.width * ratio));
    canvas.height = Math.max(1, Math.round(bounds.height * ratio));
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    draw();
  }
  function drawCell(frame, width, height) {
    if (!state.showCell || !frame.pbc.some(Boolean)) return;
    const corners = [];
    if (state.view === "3d") {
      for (let i = 0; i < 8; i += 1) corners.push(project(cart([i & 1, (i >> 1) & 1, (i >> 2) & 1], frame.cell), frame, width, height));
      context.save(); context.strokeStyle = "#91a5b1"; context.lineWidth = 1.2; context.setLineDash([]);
      for (let i = 0; i < 8; i += 1) for (const bit of [1, 2, 4]) {
        if (!(i & bit)) { const a = corners[i], b = corners[i | bit]; context.beginPath(); context.moveTo(a.x, a.y); context.lineTo(b.x, b.y); context.stroke(); }
      }
      context.restore();
    } else {
      const pairs = { ab: [0, 1], bc: [1, 2], ca: [2, 0] };
      const pair = pairs[state.view];
      [[0, 0], [1, 0], [1, 1], [0, 1]].forEach(([a, b]) => {
        const f = [0.5, 0.5, 0.5]; f[pair[0]] = a; f[pair[1]] = b;
        corners.push(project(cart(f, frame.cell), frame, width, height));
      });
      context.save(); context.beginPath(); corners.forEach((point, index) => index ? context.lineTo(point.x, point.y) : context.moveTo(point.x, point.y));
      context.closePath(); context.fillStyle = "#338c7315"; context.fill(); context.strokeStyle = "#338c7390"; context.lineWidth = 1.4; context.stroke(); context.restore();
    }
  }
  function hullFaces(vertices) {
    const faces = new Map();
    for (let i = 0; i < vertices.length - 2; i += 1) for (let j = i + 1; j < vertices.length - 1; j += 1) for (let k = j + 1; k < vertices.length; k += 1) {
      const normal0 = cross(vertices[j].map((x, a) => x - vertices[i][a]), vertices[k].map((x, a) => x - vertices[i][a]));
      if (norm(normal0) < 1e-8) continue;
      const normal = unit(normal0);
      const d = vertices.map((point) => dot(point.map((x, a) => x - vertices[i][a]), normal));
      if (d.some((x) => x > 1e-5) && d.some((x) => x < -1e-5)) continue;
      const indices = d.map((x, index) => Math.abs(x) < 1e-5 ? index : -1).filter((index) => index >= 0);
      if (indices.length < 3) continue;
      const key = indices.slice().sort((a, b) => a - b).join(",");
      if (faces.has(key)) continue;
      const centroid = [0, 1, 2].map((axis) => indices.reduce((sum, index) => sum + vertices[index][axis], 0) / indices.length);
      const u = unit(vertices[indices[0]].map((x, axis) => x - centroid[axis]));
      const v = unit(cross(normal, u));
      indices.sort((a, b) => {
        const da = vertices[a].map((x, axis) => x - centroid[axis]), db = vertices[b].map((x, axis) => x - centroid[axis]);
        return Math.atan2(dot(da, v), dot(da, u)) - Math.atan2(dot(db, v), dot(db, u));
      });
      faces.set(key, indices);
    }
    return [...faces.values()];
  }
  function projectedPolyhedronFaces(frame, width, height) {
    if (!state.showPolyhedra) return [];
    const faces = [];
    (frame.polyhedra || []).forEach((poly) => {
      const vertices = poly.vectors.map((vector) => poly.origin.map((value, axis) => value + vector[axis]));
      hullFaces(poly.vectors).forEach((indices) => {
        const points = indices.map((index) => project(vertices[index], frame, width, height));
        faces.push({ points, color: colorFor(poly.center), depth: points.reduce((sum, point) => sum + point.z, 0) / points.length });
      });
    });
    return faces;
  }
  function drawPolyhedronFace(face) {
    context.save();
    context.beginPath(); face.points.forEach((point, index) => index ? context.lineTo(point.x, point.y) : context.moveTo(point.x, point.y));
    context.closePath(); context.fillStyle = face.color; context.globalAlpha = 0.16; context.fill();
    context.globalAlpha = 0.62; context.strokeStyle = face.color; context.lineWidth = 1.15; context.stroke();
    context.restore();
  }
  function projectedBonds(frame, width, height) {
    if (!state.showBonds) return [];
    return (frame.bonds || []).map((bond) => {
      const shift = cart(bond.shift, frame.cell);
      const start = project(frame.positions[bond.i], frame, width, height);
      const end = project(frame.positions[bond.j].map((value, axis) => value + shift[axis]), frame, width, height);
      return { ...bond, start, end, depth: (start.z + end.z) / 2 };
    });
  }
  function drawBond(frame, bond) {
    const a = bond.start, b = bond.end;
    const strength = Math.max(0.3, Math.min(1, 1.3 - bond.ratio));
    const lineWidth = Math.max(1.4, Math.min(4.5, Math.min(a.scale, b.scale) * (0.024 + 0.022 * strength)));
    context.save(); context.lineCap = "round"; context.globalAlpha = 0.43 * strength; context.strokeStyle = "#203b4c";
    context.lineWidth = lineWidth + 2; context.beginPath(); context.moveTo(a.x, a.y); context.lineTo(b.x, b.y); context.stroke();
    const gradient = context.createLinearGradient(a.x, a.y, b.x, b.y);
    gradient.addColorStop(0, colorFor(frame.symbols[bond.i])); gradient.addColorStop(0.5, "#e9eff2"); gradient.addColorStop(1, colorFor(frame.symbols[bond.j]));
    context.globalAlpha = 0.85 * strength; context.strokeStyle = gradient; context.lineWidth = lineWidth;
    context.beginPath(); context.moveTo(a.x, a.y); context.lineTo(b.x, b.y); context.stroke(); context.restore();
  }
  function atomRadius(frame, index, point) {
    return Math.max(1, (displayRadii[frame.symbols[index]] || 0.9) * 0.18 * point.scale * state.atomScale);
  }
  function drawImageAtom(symbol, point) {
    const radius = Math.max(1, (displayRadii[symbol] || 0.9) * 0.18 * point.scale * state.atomScale);
    const color = colorFor(symbol);
    const gradient = context.createRadialGradient(point.x - radius * 0.32, point.y - radius * 0.38, radius * 0.08, point.x, point.y, radius);
    gradient.addColorStop(0, "#ffffff"); gradient.addColorStop(0.28, color); gradient.addColorStop(1, "#1c2d3a");
    context.fillStyle = gradient; context.beginPath(); context.arc(point.x, point.y, radius, 0, 2 * Math.PI); context.fill();
    context.strokeStyle = "#f5f9fb"; context.lineWidth = 1.1; context.stroke();
    if (state.showLabels) {
      context.fillStyle = "#172b3b"; context.font = "11px system-ui"; context.textAlign = "center";
      context.fillText(symbol, point.x, point.y - radius - 4);
    }
  }
  function drawAtom(frame, index, point) {
    const radius = atomRadius(frame, index, point);
    const value = frame.values ? frame.values[index] : NaN;
    const fill = frame.values ? scalarColor(value) : colorFor(frame.symbols[index]);
    const gradient = context.createRadialGradient(point.x - radius * 0.32, point.y - radius * 0.38, radius * 0.08, point.x, point.y, radius);
    gradient.addColorStop(0, "#ffffff"); gradient.addColorStop(0.28, fill); gradient.addColorStop(1, "#1c2d3a");
    context.fillStyle = gradient; context.beginPath(); context.arc(point.x, point.y, radius, 0, 2 * Math.PI); context.fill();
    context.strokeStyle = "#f5f9fb"; context.lineWidth = state.selectedAtom === index ? 2.7 : 1.2; context.stroke();
    if (state.selectedAtom === index) {
      context.strokeStyle = "#f1a72f"; context.lineWidth = 2.3; context.beginPath(); context.arc(point.x, point.y, radius + 4, 0, 2 * Math.PI); context.stroke();
    }
    if (state.showLabels) {
      context.fillStyle = "#172b3b"; context.font = "11px system-ui"; context.textAlign = "center";
      context.fillText(frame.symbols[index], point.x, point.y - radius - 4);
    }
    return radius;
  }
  function drawVectors(frame, width, height) {
    (frame.vectors || []).forEach((vector) => {
      const magnitude = norm(vector.vector);
      if (magnitude < 1e-12) return;
      const direction = vector.vector.map((value) => value / magnitude);
      const length = Number(vector.length) || 1.45;
      const end = vector.origin.map((value, axis) => value + direction[axis] * length);
      const a = project(vector.origin, frame, width, height), b = project(end, frame, width, height);
      context.save(); context.strokeStyle = vector.color || "#147d9b"; context.fillStyle = vector.color || "#147d9b";
      context.lineWidth = 4; context.lineCap = "round"; context.beginPath(); context.moveTo(a.x, a.y); context.lineTo(b.x, b.y); context.stroke();
      const angle = Math.atan2(b.y - a.y, b.x - a.x); const head = 9;
      context.beginPath(); context.moveTo(b.x, b.y);
      context.lineTo(b.x - head * Math.cos(angle - 0.48), b.y - head * Math.sin(angle - 0.48));
      context.lineTo(b.x - head * Math.cos(angle + 0.48), b.y - head * Math.sin(angle + 0.48));
      context.closePath(); context.fill();
      context.font = "600 11px system-ui"; context.textAlign = "left"; context.fillText(vector.label || "Vector", b.x + 7, b.y - 7);
      context.restore();
    });
  }
  function drawOrientationWidget(width, height) {
    const center = { x: width - 44, y: 44 };
    const radius = 31;
    const axisLength = 22;
    const frame = currentFrame();
    const axes = [
      { vector: [1, 0, 0], label: "X", color: "#d64b45" },
      { vector: [0, 1, 0], label: "Y", color: "#27825d" },
      { vector: [0, 0, 1], label: "Z", color: "#3978b8" },
    ].map((axis) => {
      let direction;
      if (state.view === "3d") {
        direction = rotateVector(axis.vector, state.rotation);
      } else {
        const origin = centerOf(frame);
        const start = project(origin, frame, width, height);
        const end = project(origin.map((value, i) => value + axis.vector[i]), frame, width, height);
        direction = [end.x - start.x, start.y - end.y, end.z - start.z];
        const length = Math.hypot(...direction) || 1;
        direction = direction.map((value) => value / length);
      }
      return { ...axis, direction };
    });
    axes.sort((a, b) => a.direction[2] - b.direction[2]);

    context.save();
    context.beginPath(); context.arc(center.x, center.y, radius, 0, 2 * Math.PI);
    context.fillStyle = "#ffffffed"; context.fill();
    context.strokeStyle = "#cbd8e0"; context.lineWidth = 1; context.stroke();
    axes.forEach(({ direction, label, color }) => {
      const end = {
        x: center.x + direction[0] * axisLength,
        y: center.y - direction[1] * axisLength,
      };
      const screenLength = Math.hypot(end.x - center.x, end.y - center.y);
      context.globalAlpha = direction[2] < 0 ? 0.62 : 1;
      context.strokeStyle = color; context.fillStyle = color; context.lineWidth = 2.5;
      context.lineCap = "round"; context.setLineDash(direction[2] < -0.15 ? [3, 2] : []);
      context.beginPath(); context.moveTo(center.x, center.y); context.lineTo(end.x, end.y); context.stroke();
      context.setLineDash([]);
      if (screenLength > 5) {
        const angle = Math.atan2(end.y - center.y, end.x - center.x);
        const head = 5;
        context.beginPath(); context.moveTo(end.x, end.y);
        context.lineTo(end.x - head * Math.cos(angle - 0.55), end.y - head * Math.sin(angle - 0.55));
        context.lineTo(end.x - head * Math.cos(angle + 0.55), end.y - head * Math.sin(angle + 0.55));
        context.closePath(); context.fill();
      } else {
        context.beginPath(); context.arc(end.x, end.y, 3, 0, 2 * Math.PI); context.fill();
      }
      context.globalAlpha = 1;
      const labelX = end.x + (direction[0] > 0.12 ? 3 : direction[0] < -0.12 ? -3 : 0);
      const labelY = end.y + (direction[1] > 0.12 ? -2 : direction[1] < -0.12 ? 2 : 0);
      context.font = "700 9px system-ui";
      context.textAlign = direction[0] > 0.12 ? "left" : direction[0] < -0.12 ? "right" : "center";
      context.textBaseline = direction[1] > 0.12 ? "bottom" : direction[1] < -0.12 ? "top" : "middle";
      context.lineWidth = 3; context.strokeStyle = "#ffffff"; context.strokeText(label, labelX, labelY);
      context.fillStyle = color; context.fillText(label, labelX, labelY);
    });
    context.restore();
  }
  function drawLegend(frame) {
    legend.replaceChildren();
    uniqueSymbols.forEach((symbol) => {
      const item = make("span", "legend-item");
      const swatch = make("span", "swatch"); swatch.style.background = colorFor(symbol);
      item.append(swatch, document.createTextNode(symbol)); legend.append(item);
    });
    if (frame.values) {
      const item = make("span", "legend-item");
      item.append(make("span", "valuebar"), document.createTextNode((spec.scalarName || "Value") + " · ±" + Math.abs(valueRange[1]).toPrecision(3) + " " + (spec.scalarUnits || "")));
      legend.append(item);
    }
    (frame.vectors || []).forEach((vector) => {
      const item = make("span", "legend-item");
      const swatch = make("span", "swatch"); swatch.style.background = vector.color || "#147d9b";
      item.append(swatch, document.createTextNode(vector.label + " · |v|=" + norm(vector.vector).toPrecision(3) + " " + (vector.units || "")));
      legend.append(item);
    });
  }
  function updateDetail(frame) {
    if (state.selectedAtom < 0) {
      const formula = frame.symbols.reduce((counts, symbol) => { counts[symbol] = (counts[symbol] || 0) + 1; return counts; }, {});
      const strong = make("strong", "", frame.symbols.length + " atoms");
      const summary = Object.entries(formula).map(([key, value]) => key + value).join("");
      let metrics = "";
      if (frame.pbc.some(Boolean)) {
        const lengths = frame.cell.map(norm);
        const volume = Math.abs(dot(frame.cell[0], cross(frame.cell[1], frame.cell[2])));
        metrics = " · cell " + lengths.map((value) => value.toFixed(2)).join(" × ") + " Å · " + volume.toFixed(1) + " Å³";
      }
      detail.replaceChildren(strong, document.createTextNode(" · " + summary + metrics));
      return;
    }
    const index = state.selectedAtom;
    const point = frame.positions[index];
    const value = frame.values ? " · " + (spec.scalarName || "value") + "=" + Number(frame.values[index]).toPrecision(4) + " " + (spec.scalarUnits || "") : "";
    const strong = make("strong", "", frame.symbols[index] + " " + (index + 1));
    detail.replaceChildren(strong, document.createTextNode(" · (" + point.map((x) => x.toFixed(3)).join(", ") + ") Å" + value));
  }
  let projectedAtoms = [];
  function draw() {
    const bounds = canvas.getBoundingClientRect();
    const width = bounds.width, height = bounds.height;
    if (width < 1 || height < 1) return;
    const ratio = window.devicePixelRatio || 1;
    if (canvas.width !== Math.round(width * ratio) || canvas.height !== Math.round(height * ratio)) {
      canvas.width = Math.max(1, Math.round(width * ratio)); canvas.height = Math.max(1, Math.round(height * ratio));
    }
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, width, height);
    const frame = currentFrame();
    drawCell(frame, width, height);
    const renderItems = [];
    projectedPolyhedronFaces(frame, width, height).forEach((face) => {
      renderItems.push({ depth: face.depth, order: 0, kind: "polyhedron", item: face });
    });
    projectedBonds(frame, width, height).forEach((bond) => {
      renderItems.push({ depth: bond.depth, order: 1, kind: "bond", item: bond });
    });
    const renderAtoms = frame.positions.map((position, index) => ({
      point: project(position, frame, width, height), index, symbol: frame.symbols[index], image: false,
    }));
    (frame.polyhedra || []).forEach((poly) => {
      (poly.images || []).filter((image) => image.periodic).forEach((image) => {
        renderAtoms.push({ point: project(image.position, frame, width, height), symbol: image.symbol, image: true });
      });
    });
    projectedAtoms = renderAtoms.filter((atom) => !atom.image);
    renderAtoms.forEach((atom) => {
      renderItems.push({ depth: atom.point.z, order: 2, kind: "atom", item: atom });
    });
    // Painter's order spans faces, bonds and atoms: far geometry is painted
    // first, so nearer atoms cover hidden polyhedron faces and nearer faces
    // remain visible through their translucent fill.
    renderItems.sort((a, b) => a.depth - b.depth || a.order - b.order);
    renderItems.forEach(({ kind, item }) => {
      if (kind === "polyhedron") drawPolyhedronFace(item);
      else if (kind === "bond") drawBond(frame, item);
      else if (item.image) drawImageAtom(item.symbol, item.point);
      else drawAtom(frame, item.index, item.point);
    });
    drawVectors(frame, width, height);
    drawOrientationWidget(width, height);
    const label = spec.frameLabels && spec.frameLabels[state.frame] ? spec.frameLabels[state.frame] : "frame " + (state.frame + 1);
    caption.textContent = label + (periodic ? " · " + state.view + " view" : " · interactive structure");
    frameLabel.textContent = spec.frames.length > 1 ? (state.frame + 1) + " / " + spec.frames.length : "";
    drawLegend(frame); updateDetail(frame);
  }
  function nearestAtom(x, y) {
    const frame = currentFrame();
    for (let index = projectedAtoms.length - 1; index >= 0; index -= 1) {
      const atom = projectedAtoms[index];
      const distance = Math.hypot(atom.point.x - x, atom.point.y - y);
      if (distance <= atomRadius(frame, atom.index, atom.point) + 6) return atom.index;
    }
    let winner = -1, nearest = 24;
    projectedAtoms.forEach((atom) => {
      const distance = Math.hypot(atom.point.x - x, atom.point.y - y);
      if (distance <= nearest) { winner = atom.index; nearest = distance; }
    });
    return winner;
  }
  canvas.addEventListener("pointerdown", (event) => {
    if (event.button !== 0) return;
    canvas.setPointerCapture(event.pointerId);
    state.pointer = {
      id: event.pointerId, x: event.clientX, y: event.clientY, moved: false,
      pan: event.shiftKey, roll: event.altKey && !event.shiftKey,
      ball: state.view === "3d" && !event.shiftKey && !event.altKey ? trackballPoint(event.clientX, event.clientY) : null,
    };
  });
  canvas.addEventListener("pointermove", (event) => {
    if (!state.pointer || state.pointer.id !== event.pointerId) return;
    const dx = event.clientX - state.pointer.x, dy = event.clientY - state.pointer.y;
    if (Math.abs(dx) + Math.abs(dy) > 2) state.pointer.moved = true;
    if (state.pointer.pan) { state.pan.x += dx; state.pan.y += dy; }
    else if (state.view === "3d") {
      if (state.pointer.roll) {
        const angle = dx * 0.012;
        const roll = [Math.cos(angle / 2), 0, 0, Math.sin(angle / 2)];
        state.rotation = normalizeQuaternion(quaternionMultiply(roll, state.rotation));
      } else {
        const nextBall = trackballPoint(event.clientX, event.clientY);
        rotateTrackball(state.pointer.ball, nextBall);
        state.pointer.ball = nextBall;
      }
    } else state.planeRotation += dx * 0.009;
    state.pointer.x = event.clientX; state.pointer.y = event.clientY; draw();
  });
  canvas.addEventListener("pointerup", (event) => {
    if (!state.pointer || state.pointer.id !== event.pointerId) return;
    const moved = state.pointer.moved; state.pointer = null;
    if (!moved) {
      const bounds = canvas.getBoundingClientRect();
      state.selectedAtom = nearestAtom(event.clientX - bounds.left, event.clientY - bounds.top);
    }
    draw();
  });
  canvas.addEventListener("pointercancel", () => { state.pointer = null; });
  canvas.addEventListener("wheel", (event) => {
    event.preventDefault(); state.zoom = Math.max(0.45, Math.min(3.2, state.zoom * Math.exp(-event.deltaY * 0.001))); draw();
  }, { passive: false });
  if (typeof ResizeObserver !== "undefined") new ResizeObserver(fitCanvas).observe(stage);
  draw();
}

function createMaceStructureGallery(host, spec) {
  const root = host.shadowRoot || (host.attachShadow ? host.attachShadow({ mode: "open" }) : host);
  const style = document.createElement("style");
  style.textContent = [
    ":host{display:block;font-family:Inter,ui-sans-serif,system-ui,sans-serif;color:#20394b}",
    ".gallery{overflow:hidden;border:1px solid #d9e3e9;border-radius:12px;background:#fff;box-shadow:0 3px 14px #18364b0c}",
    ".bar{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;padding:11px 14px;background:#f8fafb}",
    ".title{margin:0;color:#183c50;font-size:14px;font-weight:750}",
    ".picker{display:flex;align-items:center;gap:8px;color:#526b7b;font-size:12px;font-weight:650}",
    "select{max-width:min(70vw,420px);padding:6px 9px;border:1px solid #cbd8e0;border-radius:7px;background:#fff;color:#29495e;font:inherit;font-size:12px}",
  ].join("");
  const shell = document.createElement("section");
  shell.className = "gallery";
  const bar = document.createElement("div");
  bar.className = "bar";
  const heading = document.createElement("h3");
  heading.className = "title";
  heading.textContent = spec.title || "Explore example structures";
  const picker = document.createElement("label");
  picker.className = "picker";
  picker.append(document.createTextNode("Structure"));
  const select = document.createElement("select");
  (spec.choices || []).forEach((choice) => {
    const option = document.createElement("option");
    option.value = choice.name;
    option.textContent = choice.name;
    select.append(option);
  });
  select.value = spec.defaultChoice || (spec.choices[0] && spec.choices[0].name);
  picker.append(select);
  bar.append(heading, picker);
  const viewer = document.createElement("div");
  shell.append(bar, viewer);
  root.replaceChildren(style, shell);
  function showChoice() {
    const choice = (spec.choices || []).find((item) => item.name === select.value);
    if (!choice) return;
    const mount = document.createElement("div");
    viewer.replaceChildren(mount);
    createMaceStructureViewer(mount, choice.scene);
  }
  select.addEventListener("change", showChoice);
  showChoice();
}
