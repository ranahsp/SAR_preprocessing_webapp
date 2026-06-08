import importlib.util
import shutil
import sys

from snap_python import ensure_esa_snappy


REQUIRED_MODULES = {
    "streamlit": "streamlit",
    "folium": "folium",
    "streamlit_folium": "streamlit-folium",
    "asf_search": "asf-search",
    "numpy": "numpy",
    "requests": "requests",
}


ESA_SNAPPY_ERROR = (
    "esa_snappy could not be imported. ESA SNAP and SNAP-Python integration must "
    "already be installed and configured for the Python environment running this app. "
    "Install/configure ESA SNAP manually, then run the app again. This project will "
    "not install or configure ESA SNAP automatically."
)


def check_startup():
    errors = []

    if not shutil.which("python") and not sys.executable:
        errors.append("Python executable was not found on PATH.")

    for module_name, package_name in REQUIRED_MODULES.items():
        if importlib.util.find_spec(module_name) is None:
            errors.append(f"Missing Python dependency: {package_name}")

    module = ensure_esa_snappy(raise_on_error=False)
    if module is None:
        errors.append(ESA_SNAPPY_ERROR)

    return errors


def require_startup():
    errors = check_startup()
    if errors:
        details = "\n".join(f"- {error}" for error in errors)
        raise RuntimeError(f"Startup check failed:\n{details}")
