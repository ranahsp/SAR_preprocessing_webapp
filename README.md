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

Step 1 — Install ESA SNAP

Download and install ESA SNAP from the official ESA website:

https://step.esa.int/main/download/snap-download/

Step 2 — Configure SNAP-Python Integration

Follow the official SNAP Python (esa_snappy) configuration guide:

https://senbox.atlassian.net/wiki/spaces/SNAP/pages/19300362/How+to+use+the+SNAP-Python+snappy+interface

Make sure that esa_snappy is configured for the same Python environment that will be used to run this application.

Step 3 — Verify the Installation

Open a terminal in your Python environment and run:

python -c "import esa_snappy; print('esa_snappy OK')"

If the command prints:

esa_snappy OK

the configuration is working correctly.

Windows Users

A common SNAP Python bridge location is:

C:\Users\<USERNAME>\.snap\snap-python

If required, add this folder to your Python path before importing esa_snappy.

Example:

import sys
sys.path.append(r"C:\Users\<USERNAME>\.snap\snap-python")

import esa_snappy

If esa_snappy cannot be imported, the application will stop during startup and display an error message. Resolve the SNAP-Python configuration before running the application.

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



## Repository Hygiene

Do not commit downloaded Sentinel data, generated outputs, logs, temporary files, cache files, or Earthdata credentials. These are ignored by `.gitignore`.
