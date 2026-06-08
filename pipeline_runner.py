import argparse
import contextlib
import importlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from project_config import ROOT, ensure_runtime_dirs, resolve_project_dir
from startup_checks import require_startup


def write_netrc(username, password, target_dir):
    netrc_path = Path(target_dir) / ".earthdata_netrc"
    netrc_path.write_text(
        f"machine urs.earthdata.nasa.gov login {username} password {password}\n",
        encoding="utf-8",
    )
    try:
        os.chmod(netrc_path, 0o600)
    except OSError:
        pass
    return str(netrc_path)


@contextlib.contextmanager
def pipeline_imports(pipeline_dir):
    pipeline_path = str(ROOT / pipeline_dir)
    original_path = list(sys.path)
    modules_to_clear = [
        "sentinel_downloader",
        "preprocess_sentinel",
        "interferometry",
        "iwselection",
        "filter_sar",
    ]
    for module_name in modules_to_clear:
        sys.modules.pop(module_name, None)
    sys.path.insert(0, pipeline_path)
    try:
        yield
    finally:
        sys.path = original_path
        importlib.invalidate_caches()
        for module_name in modules_to_clear:
            sys.modules.pop(module_name, None)


def save_config(pipeline_dir, parameters):
    config_path = Path(parameters["temp_dir"]) / f"{pipeline_dir}_config_input.json"
    with config_path.open("w", encoding="utf-8") as file:
        json.dump(parameters, file, indent=2)
    print(f"Saved run configuration: {config_path}", flush=True)


def run_downloader(parameters):
    from sentinel_downloader import SentinelDownloader

    downloader = SentinelDownloader(
        start_date=datetime.strptime(parameters["start_date"], "%Y-%m-%d"),
        end_date=datetime.strptime(parameters["end_date"], "%Y-%m-%d"),
        aoi=parameters["subset_wkt"],
        download_dir=parameters["download_dir"],
        netrc_path=parameters["netrc_path"],
    )
    return downloader.run()


def select_and_filter_safe_paths(parameters, safe_paths, pol="VV"):
    from filter_sar import Filter_sar
    from iwselection import SubswathSelector

    selector = SubswathSelector(aoi_wkt=parameters["subset_wkt"], pol=pol)
    selected_subswath = selector.select_best_subswath(
        safe_paths=safe_paths,
        enforce_same_orbit=True,
        verbose=True,
    )
    print(f"Selected subswath: {selected_subswath}", flush=True)

    filtered_safe_paths = Filter_sar.filter_images(
        safe_paths,
        parameters["subset_wkt"],
        subswath=selected_subswath,
    )
    filtered_json_path = Path(parameters["download_dir"]) / "filtered_safe_paths.json"
    with filtered_json_path.open("w", encoding="utf-8") as file:
        json.dump(filtered_safe_paths, file, indent=2)
    print(f"Saved filtered SAFE paths: {filtered_json_path}", flush=True)
    return selected_subswath, filtered_safe_paths


def run_backscatter(parameters):
    with pipeline_imports("backscatter"):
        from preprocess_sentinel import PreprocessSentinel1

        save_config("backscatter", parameters)
        safe_paths = run_downloader(parameters)
        selected_subswath, filtered_safe_paths = select_and_filter_safe_paths(
            parameters,
            safe_paths,
            pol="VV",
        )

        processor = PreprocessSentinel1(
            wkt_st=parameters["subset_wkt"],
            output_folder_path=parameters["output_folder_path"],
            export_intermediate=parameters["export_intermediate"],
            print_operators=parameters["print_operators"],
            subswath=selected_subswath,
        )

        for filename, safe_path in filtered_safe_paths.items():
            print(f"\nStarting backscatter preprocessing for {filename}", flush=True)
            processor.run(label=filename, safe_path=safe_path)

        print("\n--- Pipeline Complete: Backscatter products generated ---", flush=True)


def run_coherence(parameters):
    with pipeline_imports("coherence"):
        from interferometry import InterferometryProcessor

        save_config("coherence", parameters)
        safe_paths = run_downloader(parameters)
        selected_subswath, filtered_safe_paths = select_and_filter_safe_paths(
            parameters,
            safe_paths,
        )

        ordered_paths = list(filtered_safe_paths.items())[::-1]
        if len(ordered_paths) < 2:
            raise RuntimeError("Coherence preprocessing requires at least two matching SLC scenes.")

        pairs = [(ordered_paths[i], ordered_paths[i + 1]) for i in range(len(ordered_paths) - 1)]
        print(f"Prepared {len(pairs)} interferometric pair(s).", flush=True)

        processor = InterferometryProcessor(
            subswath=selected_subswath,
            output_folder=parameters["output_folder_path"],
            wkt=parameters["subset_wkt"],
        )

        for index, (master, slave) in enumerate(pairs, start=1):
            master_name, master_path = master
            slave_name, slave_path = slave
            master_date = Path(master_path).name.split("_")[5][:8]
            slave_date = Path(slave_path).name.split("_")[5][:8]
            output_name = f"interferogram_{index}_{master_date}_vs_{slave_date}"
            print(f"\nStarting coherence pair {index}: {master_name} / {slave_name}", flush=True)
            processor.run(
                master_path=master_path,
                slave_path=slave_path,
                output_base_name=output_name,
            )
            print(f"Processed pair {index}: {master_date} & {slave_date}", flush=True)

        print("\n--- Pipeline Complete: Coherence products generated ---", flush=True)


def parse_args():
    parser = argparse.ArgumentParser(description="Run Sentinel-1 preprocessing from Streamlit.")
    parser.add_argument("--mode", choices=["backscatter", "coherence"], required=True)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--download-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--start-date", required=True)
    parser.add_argument("--end-date", required=True)
    parser.add_argument("--wkt", required=True)
    return parser.parse_args()


def main():
    require_startup()
    runtime_dirs = ensure_runtime_dirs()
    args = parse_args()
    download_dir = resolve_project_dir(args.download_dir, "Download directory")
    output_dir = resolve_project_dir(args.output_dir, "Output directory")
    temp_dir = runtime_dirs["tmp"]
    netrc_path = write_netrc(args.username, args.password, temp_dir)

    parameters = {
        "subset_wkt": args.wkt,
        "netrc_path": netrc_path,
        "start_date": args.start_date,
        "end_date": args.end_date,
        "download_dir": str(download_dir),
        "output_folder_path": str(output_dir),
        "temp_dir": str(temp_dir),
        "export_intermediate": False,
        "print_operators": False,
    }

    print(f"Running {args.mode} preprocessing", flush=True)
    print(f"Date range: {args.start_date} to {args.end_date}", flush=True)
    print(f"Download directory: {download_dir}", flush=True)
    print(f"Output directory: {output_dir}", flush=True)

    if args.mode == "backscatter":
        run_backscatter(parameters)
    else:
        run_coherence(parameters)


if __name__ == "__main__":
    main()
