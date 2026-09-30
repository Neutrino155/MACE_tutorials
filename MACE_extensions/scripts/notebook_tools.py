"""Small presentation helpers shared by the extension notebooks."""
from __future__ import annotations

from html import escape
import inspect
import os
import subprocess
import sys
import time
from pathlib import Path

from IPython.display import HTML, display
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer


_FORMATTER = HtmlFormatter(style="friendly", linenos="table", cssclass="mace-snippet")
_STYLE = _FORMATTER.get_style_defs(".mace-snippet") + r"""
.mace-source{margin:12px 0;border:1px solid #d9e3e9;border-radius:10px;overflow:hidden;background:#fff;box-shadow:0 3px 14px #18364b0c}
.mace-source summary{display:flex;align-items:center;gap:9px;padding:10px 13px;cursor:pointer;list-style:none;background:#f2f6f8;color:#203b4d;font:600 13px/1.4 Inter,system-ui,sans-serif}
.mace-source summary::-webkit-details-marker{display:none}
.mace-source summary:before{content:'+';display:inline-grid;place-items:center;width:19px;height:19px;border-radius:5px;background:#dce9eb;color:#206b70;font:700 15px/1 system-ui}
.mace-source[open] summary:before{content:'−'}
.mace-source .source-tag{margin-left:auto;padding:3px 7px;border-radius:5px;background:#e3eef0;color:#28676b;font:700 9px/1.2 Inter,system-ui,sans-serif;letter-spacing:.08em;text-transform:uppercase}
.mace-source .source-path{padding:8px 13px 0;color:#657b89;font:11px/1.4 ui-monospace,SFMono-Regular,monospace}
.mace-source .source-note{padding:6px 13px 0;color:#657b89;font:11px/1.4 Inter,system-ui,sans-serif}
.mace-source .highlight{max-height:480px;overflow:auto;margin:9px 10px 11px;border:1px solid #e1e8ec;border-radius:7px;background:#f7f9fa;font:11px/1.5 ui-monospace,SFMono-Regular,monospace}
.mace-source .highlight pre{margin:0;padding:10px 12px;background:transparent}
.mace-source .highlighttable{width:100%;border-spacing:0}.mace-source .highlighttable pre{white-space:pre}
.mace-source .linenos{position:sticky;left:0;padding:10px 8px;border-right:1px solid #e1e8ec;background:#f0f4f6;color:#8a9ba5;text-align:right;user-select:none}
"""


def _show_source(source: str, *, title: str, location: str, first_line: int = 1, note: str = "") -> None:
    formatter = HtmlFormatter(style="friendly", linenos="table", linenostart=first_line, cssclass="mace-snippet")
    body = highlight(source, PythonLexer(), formatter)
    html = (
        f'<details class="mace-source"><summary>{escape(title)}'
        '<span class="source-tag">Python source</span></summary>'
        f'<div class="source-path">{escape(location)}</div>'
        + (f'<div class="source-note">{escape(note)}</div>' if note else "")
        + body + f'<style>{_STYLE}</style></details>'
    )
    display(HTML(html))


def show_source_hits(obj, needles, context: int = 5, max_chars: int = 12000) -> None:
    """Display the source lines around each requested token."""
    lines, first_line = inspect.getsourcelines(obj)
    hits = [i for i, line in enumerate(lines) if any(token in line for token in needles)]
    spans: list[tuple[int, int]] = []
    for hit in hits:
        start, stop = max(0, hit - context), min(len(lines), hit + context + 1)
        if spans and start <= spans[-1][1]:
            spans[-1] = (spans[-1][0], max(spans[-1][1], stop))
        else:
            spans.append((start, stop))
    if not spans:
        raise ValueError(f"No requested source tokens found in {obj.__qualname__}")
    source = "\n".join(line.rstrip("\n") for start, stop in spans for line in lines[start:stop])
    truncated = len(source) > max_chars
    source = source[:max_chars]
    path = inspect.getsourcefile(obj) or "Python source"
    _show_source(
        source, title=obj.__qualname__, location=path, first_line=first_line,
        note="Excerpt shortened to keep the source view compact." if truncated else "",
    )


def read_source(relative_path: str, start: int, stop: int, *, root: str | Path) -> None:
    """Display a numbered source range from the installed MACE-Field checkout."""
    path = Path(root) / relative_path
    lines = path.read_text(encoding="utf-8").splitlines()
    if start < 1 or stop < start or start > len(lines):
        raise ValueError(f"Invalid source range {start}:{stop} for {path}")
    stop = min(stop, len(lines))
    source = "\n".join(lines[start - 1:stop])
    _show_source(source, title=path.name, location=f"{path} · lines {start}–{stop}", first_line=start)


def train_mace(config: dict) -> Path:
    """Write a MACE config and stream its debug log without duplicate handlers."""
    import yaml

    config = dict(config)
    model_dir = Path(config["model_dir"]).expanduser().resolve()
    model_dir.mkdir(parents=True, exist_ok=True)
    config["model_dir"] = str(model_dir)
    for key, folder in {
        "checkpoints_dir": "checkpoints",
        "log_dir": "logs",
        "results_dir": "results",
        "work_dir": "work",
    }.items():
        config.setdefault(key, str(model_dir / folder))
    config_path = model_dir / "training.yml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    # MACE's setup_logger adds handlers to the process-wide root logger. Running
    # several fits in a notebook kernel therefore stacks console handlers and
    # repeats every line. A fresh CLI process avoids that state leaking between
    # fits; stream only its debug log into the cell output.
    environment = os.environ.copy()
    environment["PYTHONWARNINGS"] = "ignore::UserWarning,ignore::DeprecationWarning"
    runtime_paths = [str(Path.cwd())]
    runtime_paths.extend(
        str(Path(path).expanduser().resolve())
        for path in sys.path
        if path and Path(path).expanduser().exists()
    )
    if environment.get("PYTHONPATH"):
        runtime_paths.extend(environment["PYTHONPATH"].split(os.pathsep))
    environment["PYTHONPATH"] = os.pathsep.join(dict.fromkeys(runtime_paths))

    seed = config.get("seed", 123)
    tag = f"{config['name']}_run-{seed}"
    debug_log = Path(config["log_dir"]) / f"{tag}_debug.log"
    offset = debug_log.stat().st_size if debug_log.exists() else 0
    command = [
        sys.executable,
        "-m",
        "mace.cli.run_train",
        "--config",
        str(config_path),
    ]
    process = subprocess.Popen(command, env=environment, stdout=subprocess.DEVNULL)

    def stream_new_log_content() -> None:
        nonlocal offset
        if not debug_log.is_file():
            return
        size = debug_log.stat().st_size
        if size < offset:  # The logger recreated the file for this run.
            offset = 0
        with debug_log.open("rb") as log_file:
            log_file.seek(offset)
            chunk = log_file.read()
            offset = log_file.tell()
        if chunk:
            sys.stdout.write(chunk.decode("utf-8", errors="replace"))
            sys.stdout.flush()

    try:
        while process.poll() is None:
            stream_new_log_content()
            time.sleep(0.2)
        stream_new_log_content()
    except BaseException:
        if process.poll() is None:
            process.terminate()
            process.wait()
        raise
    if process.returncode:
        raise subprocess.CalledProcessError(process.returncode, command)
    return config_path


def run_python_script(
    script: str | Path,
    *arguments: str | Path,
    python_path: tuple[str | Path, ...] = (),
) -> None:
    """Run a repository CLI in a clean Python process with the source paths set."""
    script = Path(script).resolve()
    environment = os.environ.copy()
    paths = [str(Path(path).resolve()) for path in python_path]
    if environment.get("PYTHONPATH"):
        paths.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(paths)
    environment["PYTHONWARNINGS"] = "ignore::UserWarning,ignore::DeprecationWarning"
    command = [sys.executable, str(script), *(str(argument) for argument in arguments)]
    process = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    if process.stdout:
        sys.stdout.write(process.stdout)
        sys.stdout.flush()
    if process.stderr:
        sys.stderr.write(process.stderr)
        sys.stderr.flush()
    if process.returncode:
        raise subprocess.CalledProcessError(
            process.returncode, command, output=process.stdout, stderr=process.stderr
        )


def require_clean_source(source: str | Path, branch: str = "origin/develop") -> str:
    """Require an unmodified MACE source tree at the requested branch tip."""
    import subprocess

    source = Path(source)
    head = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    target = subprocess.run(
        ["git", "-C", str(source), "rev-parse", branch],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    changed = subprocess.run(
        ["git", "-C", str(source), "diff", "--quiet", "HEAD", "--", "mace"],
        check=False,
    ).returncode
    if head != target or changed:
        raise RuntimeError(
            f"Training needs a clean MACE source tree at {branch}; source is {head}, "
            f"reference is {target}."
        )
    return head
