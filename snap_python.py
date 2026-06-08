import importlib
import os
import sys
from pathlib import Path


_LAST_RESULT = None


def _candidate_snap_python_paths():
    home = Path.home()
    candidates = []

    env_path = os.getenv("SNAP_PYTHON")
    if env_path:
        candidates.append(Path(env_path).expanduser())

    user_profile = os.getenv("USERPROFILE")
    if user_profile:
        candidates.append(Path(user_profile) / ".snap" / "snap-python")

    candidates.append(home / ".snap" / "snap-python")

    unique_candidates = []
    seen = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved not in seen:
            unique_candidates.append(resolved)
            seen.add(resolved)
    return unique_candidates


def ensure_esa_snappy(raise_on_error=True, print_diagnostics=True):
    global _LAST_RESULT

    if _LAST_RESULT and _LAST_RESULT["success"]:
        return _LAST_RESULT["module"]

    home = Path.home().resolve()
    python_executable = Path(sys.executable).resolve()
    selected_snap_python_path = None
    import_error = None

    try:
        module = importlib.import_module("esa_snappy")
        _LAST_RESULT = {
            "success": True,
            "module": module,
            "home": home,
            "python_executable": python_executable,
            "snap_python_path": selected_snap_python_path,
            "import_error": None,
        }
        _print_diagnostics(_LAST_RESULT, print_diagnostics)
        return module
    except Exception as exc:
        import_error = exc

    for candidate in _candidate_snap_python_paths():
        if candidate.exists() and candidate.is_dir():
            selected_snap_python_path = candidate
            candidate_text = str(candidate)
            if candidate_text not in sys.path:
                sys.path.insert(0, candidate_text)
            try:
                module = importlib.import_module("esa_snappy")
                _LAST_RESULT = {
                    "success": True,
                    "module": module,
                    "home": home,
                    "python_executable": python_executable,
                    "snap_python_path": selected_snap_python_path,
                    "import_error": None,
                }
                _print_diagnostics(_LAST_RESULT, print_diagnostics)
                return module
            except Exception as exc:
                import_error = exc

    _LAST_RESULT = {
        "success": False,
        "module": None,
        "home": home,
        "python_executable": python_executable,
        "snap_python_path": selected_snap_python_path,
        "import_error": import_error,
    }
    _print_diagnostics(_LAST_RESULT, print_diagnostics)

    if raise_on_error:
        raise ImportError(
            "esa_snappy could not be imported after checking the current Python "
            "environment and common current-user SNAP Python locations."
        ) from import_error
    return None


def _print_diagnostics(result, enabled):
    if not enabled:
        return

    snap_path = result["snap_python_path"]
    if snap_path is None:
        detected_snap_path = "not found or not needed"
    else:
        detected_snap_path = str(snap_path)

    print("SNAP Python diagnostics:", flush=True)
    print(f"  Home directory: {result['home']}", flush=True)
    print(f"  SNAP Python path: {detected_snap_path}", flush=True)
    print(f"  Python executable: {result['python_executable']}", flush=True)
    print(f"  esa_snappy import succeeded: {result['success']}", flush=True)
    if result["import_error"]:
        print(f"  esa_snappy import error: {result['import_error']}", flush=True)
