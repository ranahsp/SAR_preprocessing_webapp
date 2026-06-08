import os
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_DOWNLOAD_DIR = "downloads"
DEFAULT_OUTPUT_DIR = "outputs"
DEFAULT_LOG_DIR = "logs"
DEFAULT_TEMP_DIR = "tmp"


def load_dotenv(path=None):
    env_path = Path(path) if path else ROOT / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def project_path(value, default):
    configured = value or default
    path = Path(configured).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    path = path.resolve()
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError(f"Runtime directory must be inside the project directory: {ROOT}") from exc
    return path


def get_runtime_dirs():
    load_dotenv()
    return {
        "downloads": project_path(os.getenv("SAR_DOWNLOAD_DIR"), DEFAULT_DOWNLOAD_DIR),
        "outputs": project_path(os.getenv("SAR_OUTPUT_DIR"), DEFAULT_OUTPUT_DIR),
        "logs": project_path(os.getenv("SAR_LOG_DIR"), DEFAULT_LOG_DIR),
        "tmp": project_path(os.getenv("SAR_TEMP_DIR"), DEFAULT_TEMP_DIR),
    }


def ensure_runtime_dirs():
    dirs = get_runtime_dirs()
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def resolve_project_dir(value, label):
    path = project_path(value, "")
    path.mkdir(parents=True, exist_ok=True)
    return path
