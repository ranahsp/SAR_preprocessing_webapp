FROM python:3.10-slim-bookworm

ARG SNAP_INSTALLER_URL=https://download.esa.int/step/snap/13.0/installers/esa-snap_all_linux-13.0.0.sh

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PYTHONIOENCODING=utf-8 \
    SNAP_HOME=/opt/snap \
    SNAP_PYTHON=/root/.snap/snap-python

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    fontconfig \
    libfreetype6 \
    libgl1 \
    libglib2.0-0 \
    libx11-6 \
    libxext6 \
    libxi6 \
    libxrender1 \
    libxtst6 \
    wget \
    unzip \
    && rm -rf /var/lib/apt/lists/*

RUN wget -O /tmp/esa-snap-installer.sh "$SNAP_INSTALLER_URL" \
    && chmod +x /tmp/esa-snap-installer.sh \
    && /tmp/esa-snap-installer.sh -q -dir "$SNAP_HOME" \
    && rm /tmp/esa-snap-installer.sh

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN "$SNAP_HOME/bin/snappy-conf" /usr/local/bin/python

COPY . .
RUN mkdir -p /app/downloads /app/outputs

EXPOSE 8501

CMD ["python", "-m", "streamlit", "run", "app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
