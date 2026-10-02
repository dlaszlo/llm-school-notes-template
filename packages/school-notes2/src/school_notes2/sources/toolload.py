"""Load a helper from the release's `tools/` folder (drive_media, prepare_photo).

The helpers live at the template root, outside this package; the release keeps them next to
it, so the tool always runs its own copy and never the learner worktree's `tools/`.
"""

import importlib.util
import sys
from pathlib import Path

# src/school_notes2/sources/toolload.py -> parents[5] is the template root.
DEFAULT_TOOLS_DIR = Path(__file__).resolve().parents[5] / "tools"


def load_tool(name: str, tools_dir: Path | None = None):
    tools_dir = Path(tools_dir or DEFAULT_TOOLS_DIR).resolve()
    key = f"_sn_tool_{name}_{abs(hash(str(tools_dir)))}"
    if key in sys.modules:
        return sys.modules[key]
    path = tools_dir / f"{name}.py"
    if not path.is_file():
        raise ImportError(f"tool {name} not found in {tools_dir}")
    spec = importlib.util.spec_from_file_location(key, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[key] = module
    spec.loader.exec_module(module)
    return module
