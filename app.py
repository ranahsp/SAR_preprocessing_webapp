import json
import queue
import re
import subprocess
import sys
import threading
import time
import os
from html import escape
from datetime import date, timedelta
from pathlib import Path

import folium
import streamlit as st
from folium.plugins import Draw
from streamlit_folium import st_folium


ROOT = Path(__file__).resolve().parent
EARTHDATA_REGISTER_URL = "https://urs.earthdata.nasa.gov/users/new"
DEFAULT_WKT = (
    "POLYGON((9.781406838574448 46.14320614003389, "
    "9.720482133037649 45.95891875411276, "
    "10.161831199337202 45.887383816581746, "
    "10.224332317841158 46.07048731922457, "
    "9.781406838574448 46.14320614003389))"
)


def polygon_coords_from_wkt(wkt):
    match = re.match(r"^\s*POLYGON\s*\(\((.+)\)\)\s*$", wkt, flags=re.IGNORECASE)
    if not match:
        return []
    coords = []
    for pair in match.group(1).split(","):
        parts = pair.strip().split()
        if len(parts) < 2:
            return []
        lon, lat = float(parts[0]), float(parts[1])
        coords.append((lat, lon))
    return coords


def geojson_polygon_to_wkt(geometry):
    if not geometry or geometry.get("type") != "Polygon":
        return None
    rings = geometry.get("coordinates") or []
    if not rings:
        return None
    coords = rings[0]
    if coords[0] != coords[-1]:
        coords = coords + [coords[0]]
    coord_text = ", ".join(f"{lon} {lat}" for lon, lat in coords)
    return f"POLYGON(({coord_text}))"


def build_map(wkt):
    coords = polygon_coords_from_wkt(wkt)
    center = [46.02, 9.97]
    zoom = 10
    if coords:
        center = [
            sum(point[0] for point in coords) / len(coords),
            sum(point[1] for point in coords) / len(coords),
        ]
        zoom = 11

    fmap = folium.Map(location=center, zoom_start=zoom, control_scale=True, tiles="OpenStreetMap")
    if coords:
        folium.Polygon(
            locations=coords,
            color="#f97316",
            weight=3,
            fill=True,
            fill_color="#f97316",
            fill_opacity=0.18,
            tooltip="Current AOI",
        ).add_to(fmap)
        fmap.fit_bounds(coords)

    Draw(
        export=False,
        draw_options={
            "polyline": False,
            "rectangle": True,
            "circle": False,
            "marker": False,
            "circlemarker": False,
            "polygon": True,
        },
        edit_options={"edit": True, "remove": True},
    ).add_to(fmap)
    return fmap


def format_elapsed(seconds):
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def enqueue_stream(stream, output_queue, label):
    for line in iter(stream.readline, ""):
        timestamp = time.strftime("%H:%M:%S")
        output_queue.put(f"[{timestamp}] [{label}] {line}")
    stream.close()


def render_console(placeholder, logs, elapsed_seconds=None):
    elapsed_text = ""
    if elapsed_seconds is not None:
        elapsed_text = f"<div class='elapsed'>Running time: {escape(format_elapsed(elapsed_seconds))}</div>"

    content = escape("".join(logs))
    if not content:
        content = "Waiting for pipeline output..."

    placeholder.markdown(
        f"""
        <div class="console-wrap">
            {elapsed_text}
            <pre>{content}</pre>
        </div>
        <style>
            .console-wrap {{
                border: 1px solid rgba(226, 232, 240, 0.88);
                border-radius: 8px;
                background: rgba(255, 255, 255, 0.96);
                color: #0f172a;
                height: 460px;
                overflow: auto;
                padding: 0;
                font-family: Consolas, "Courier New", monospace;
                font-size: 13px;
                line-height: 1.5;
                white-space: pre-wrap;
                box-shadow: 0 18px 55px rgba(0, 0, 0, 0.26);
            }}
            .console-wrap .elapsed {{
                color: #0f172a;
                font-weight: 600;
                position: sticky;
                top: 0;
                background: rgba(248, 250, 252, 0.98);
                border-bottom: 1px solid rgba(203, 213, 225, 0.92);
                padding: 12px 16px;
            }}
            .console-wrap pre {{
                margin: 0;
                padding: 14px 16px 16px;
                white-space: pre-wrap;
                overflow-wrap: anywhere;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def run_pipeline(command):
    output_queue = queue.Queue()
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    start_time = time.time()

    process = subprocess.Popen(
        command,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        env=env,
    )

    threads = [
        threading.Thread(target=enqueue_stream, args=(process.stdout, output_queue, "stdout"), daemon=True),
        threading.Thread(target=enqueue_stream, args=(process.stderr, output_queue, "stderr"), daemon=True),
    ]
    for thread in threads:
        thread.start()

    logs = []
    console = st.empty()
    status = st.empty()

    while process.poll() is None or not output_queue.empty():
        while not output_queue.empty():
            logs.append(output_queue.get_nowait())
        elapsed = time.time() - start_time
        render_console(console, logs, elapsed_seconds=elapsed)
        status.info(f"Pipeline is running... elapsed {format_elapsed(elapsed)}")
        time.sleep(0.5)

    for thread in threads:
        thread.join(timeout=1)

    return_code = process.returncode
    while not output_queue.empty():
        logs.append(output_queue.get_nowait())
    render_console(console, logs, elapsed_seconds=time.time() - start_time)

    if return_code == 0:
        status.success("Pipeline finished successfully.")
    else:
        status.error(f"Pipeline failed with exit code {return_code}.")

    return return_code, "".join(logs)


def init_session_state():
    st.session_state.setdefault("aoi_wkt", DEFAULT_WKT)


def inject_page_style():
    st.markdown(
        """
        <style>
            .stApp {{
                background: linear-gradient(180deg, #dff3ff 0%, #eef9ff 44%, #f8fcff 100%);
            }}
            [data-testid="stHeader"] {{
                background: rgba(223, 243, 255, 0.86);
            }}
            [data-testid="stSidebar"] {{
                background: linear-gradient(180deg, #d8efff 0%, #eef8ff 100%);
                border-right: 1px solid rgba(59, 130, 246, 0.22);
            }}
            [data-testid="stSidebar"] * {{
                color: #0f3b5f;
            }}
            .block-container {{
                padding-top: 2rem;
                padding-bottom: 3rem;
            }}
            .main h1, .main h2, .main h3, .main p, .main label,
            .main .stMarkdown, .main [data-testid="stCaptionContainer"],
            .main [data-testid="stWidgetLabel"], .main [data-testid="stMarkdownContainer"] {{
                color: #0f3b5f !important;
            }}
            .main [data-testid="stHeading"] *,
            .main [data-testid="stMarkdownContainer"] h1,
            .main [data-testid="stMarkdownContainer"] h2,
            .main [data-testid="stMarkdownContainer"] h3 {{
                color: #0f3b5f !important;
            }}
            .main .stTextArea textarea,
            .main .stTextInput input {{
                background: rgba(255, 255, 255, 0.94);
                border: 1px solid rgba(186, 213, 242, 0.75);
                color: #0f172a;
            }}
            [data-testid="stVerticalBlockBorderWrapper"],
            [data-testid="stForm"],
            [data-testid="stExpander"] {{
                background: rgba(255, 255, 255, 0.72);
                border: 1px solid rgba(96, 165, 250, 0.22);
                border-radius: 8px;
                box-shadow: 0 14px 36px rgba(59, 130, 246, 0.12);
                backdrop-filter: blur(6px);
            }}
            iframe {{
                border-radius: 8px;
                box-shadow: 0 14px 36px rgba(37, 99, 235, 0.16);
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(page_title="Sentinel-1 SAR Pipeline", layout="wide")
    inject_page_style()
    init_session_state()

    st.title("Sentinel-1 SAR Processing")

    with st.sidebar:
        st.header("Authentication")
        username = st.text_input("ASF / NASA Earthdata Username")
        password = st.text_input("ASF / NASA Earthdata Password", type="password")
        st.markdown(f"[Create an account]({EARTHDATA_REGISTER_URL})")

        st.header("Folders")
        download_dir = st.text_input("Download Directory", value=str(ROOT / "downloads"))
        output_dir = st.text_input("Output Directory", value=str(ROOT / "outputs"))

        st.header("Time Series")
        default_end = date.today()
        default_start = default_end - timedelta(days=12)
        start_date = st.date_input("Start Date", value=default_start)
        end_date = st.date_input("End Date", value=default_end)

        st.header("Processing")
        processing_label = st.radio(
            "Preprocessing type",
            ["Backscatter preprocessing", "Coherence preprocessing"],
        )

    left, right = st.columns([1.25, 1])

    with left:
        st.subheader("Area of Interest")
        map_data = st_folium(
            build_map(st.session_state.aoi_wkt),
            height=560,
            width=None,
            returned_objects=["last_active_drawing", "all_drawings"],
        )

        drawing = map_data.get("last_active_drawing") if map_data else None
        drawn_wkt = geojson_polygon_to_wkt(drawing.get("geometry")) if drawing else None
        if drawn_wkt and drawn_wkt != st.session_state.aoi_wkt:
            st.session_state.aoi_wkt = drawn_wkt
            st.rerun()

    with right:
        st.subheader("AOI WKT")
        wkt_input = st.text_area(
            "Polygon WKT",
            value=st.session_state.aoi_wkt,
            height=180,
            help="Paste a POLYGON WKT or draw a polygon/rectangle on the map.",
        )
        if wkt_input != st.session_state.aoi_wkt:
            st.session_state.aoi_wkt = wkt_input.strip()

        coords = polygon_coords_from_wkt(st.session_state.aoi_wkt)
        if coords:
            st.caption(f"AOI vertices: {len(coords)}")
        else:
            st.warning("Enter a valid POLYGON WKT before running the pipeline.")

        run_disabled = not all(
            [
                username.strip(),
                password,
                download_dir.strip(),
                output_dir.strip(),
                coords,
                start_date <= end_date,
            ]
        )

        if start_date > end_date:
            st.error("Start Date must be before or equal to End Date.")

        st.divider()
        run_clicked = st.button("Run Pipeline", type="primary", disabled=run_disabled)

    if run_clicked:
        mode = "backscatter" if processing_label.startswith("Backscatter") else "coherence"
        command = [
            sys.executable,
            "-X",
            "utf8",
            "-u",
            str(ROOT / "pipeline_runner.py"),
            "--mode",
            mode,
            "--username",
            username,
            "--password",
            password,
            "--download-dir",
            download_dir,
            "--output-dir",
            output_dir,
            "--start-date",
            start_date.isoformat(),
            "--end-date",
            end_date.isoformat(),
            "--wkt",
            st.session_state.aoi_wkt,
        ]
        return_code, logs = run_pipeline(command)
        st.download_button(
            "Download Console Log",
            data=logs,
            file_name=f"sentinel1_{mode}_pipeline.log",
            mime="text/plain",
        )
        if return_code != 0:
            st.stop()


if __name__ == "__main__":
    main()
