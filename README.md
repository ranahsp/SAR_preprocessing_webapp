# Sentinel-1 SAR Streamlit App

Streamlit web app for Sentinel-1 SAR preprocessing with backscatter and coherence workflows.

This project is portable across computers, but it does not install ESA SNAP or configure SNAP-Python integration. Each user must do that in their own local Python environment before running the app.

## Requirements

- Python 3.9+
- ESA SNAP Desktop installed by the user
- `esa_snappy` configured by the user for the same Python environment used to run this app
- NASA Earthdata / ASF account
- Enough disk space for Sentinel-1 downloads and generated products

## Configure ESA SNAP

Install ESA SNAP from ESA's official distribution and configure SNAP-Python integration for your local Python environment.

After configuration, verify this works from the project environment:

```powershell
python -c "import esa_snappy; print('esa_snappy OK')"
```

If that command fails, the app will also try the current user's common SNAP Python bridge directory, such as `%USERPROFILE%\.snap\snap-python` on Windows or `~/.snap/snap-python` on Linux/macOS. If `esa_snappy` still cannot be imported, fix the ESA SNAP Python integration first. The application startup check will stop with a clear error until `esa_snappy` imports successfully.

## Install Project Dependencies

Create or activate the Python environment you want to use, then install the project packages:

```powershell
python -m pip install -r requirements.txt
```

## Runtime Directories

By default, runtime files are stored inside the project:

- `downloads/` for Sentinel-1 ZIP and SAFE products
- `outputs/` for generated GeoTIFF products
- `logs/` for local logs
- `tmp/` for generated run configuration and temporary Earthdata credentials

Copy `.env.example` to `.env` only if you want to change these project-relative folder names:

```powershell
copy .env.example .env
```

Keep the directory values relative to the project folder. The app validates runtime directories so generated files stay inside the project.

## Run Locally

```powershell
python -m streamlit run app.py
```

Or double-click:

```text
run_app.bat
```

Then open:

```text
http://localhost:8501
```

The app runs a startup check before showing the workflow. It verifies Python, required project dependencies, and `esa_snappy`.

## Share on the Same Network

Run:

```powershell
python -m streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

Find your computer IP:

```powershell
ipconfig
```

Send coworkers this address:

```text
http://YOUR-IP:8501
```

Your computer must stay on and the app must keep running. Coworkers still need their own Earthdata credentials when running their own copy.

## Docker Note

The included Dockerfile installs only Python project dependencies. It does not install ESA SNAP or run SNAP-Python configuration.

Use Docker only if your image/container environment already has a working `esa_snappy` configuration. For most users, running the app locally in the configured Python environment is the recommended path.

## Repository Hygiene

Do not commit downloaded Sentinel data, generated outputs, logs, temporary files, cache files, or Earthdata credentials. These are ignored by `.gitignore`.
