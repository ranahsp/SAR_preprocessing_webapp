# Sentinel-1 SAR Streamlit App

Streamlit web app for Sentinel-1 SAR preprocessing with backscatter and coherence workflows.

## Requirements

- Python 3.9+
- ESA SNAP Desktop installed
- ESA SNAPPY configured for the Python environment
- NASA Earthdata / ASF account
- Enough disk space for Sentinel-1 downloads and outputs

Install Python dependencies:

```powershell
pip install -r requirements.txt
```

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

Your computer must stay on and the app must keep running.

## GitHub Notes

Do not commit downloaded Sentinel data, generated outputs, logs, cache files, or Earthdata credentials. These are ignored by `.gitignore`.

Each user should enter their own Earthdata credentials in the app.

## Run With Docker

Build the image:

```powershell
docker build -t sentinel-sar-app .
```

Run the app:

```powershell
docker run --rm -p 8501:8501 -v ${PWD}/downloads:/app/downloads -v ${PWD}/outputs:/app/outputs sentinel-sar-app
```

Then open:

```text
http://localhost:8501
```

Or use Docker Compose:

```powershell
docker compose up --build
```

The Docker image installs ESA SNAP inside Linux. The first build downloads the SNAP installer, which is large and can take time.

## Publish Docker Image From GitHub

This repository includes a GitHub Actions workflow at:

```text
.github/workflows/docker-publish.yml
```

After the code is pushed to the `main` branch, GitHub can build and publish the image to GitHub Container Registry:

```text
ghcr.io/YOUR-GITHUB-USERNAME/YOUR-REPOSITORY:latest
```

Coworkers can run the published image with:

```powershell
docker run --rm -p 8501:8501 -v ${PWD}/downloads:/app/downloads -v ${PWD}/outputs:/app/outputs ghcr.io/YOUR-GITHUB-USERNAME/YOUR-REPOSITORY:latest
```
