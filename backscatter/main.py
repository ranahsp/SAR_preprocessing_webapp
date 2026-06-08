import json
import os
import argparse
from datetime import datetime
from pathlib import Path
from sentinel_downloader import SentinelDownloader
from preprocess_sentinel import PreprocessSentinel1
from iwselection import SubswathSelector
from filter_sar import Filter_sar


def load_parameters():
    parser = argparse.ArgumentParser(description="Run the backscatter pipeline from a JSON config file.")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parents[1] / "tmp" / "backscatter_config_input.json"),
        help="Path to a pipeline JSON config file.",
    )
    args = parser.parse_args()
    with open(args.config, "r", encoding="utf-8") as file:
        return json.load(file)


def main():
    parameters = load_parameters()

    downloader = SentinelDownloader(
        start_date=datetime.strptime(parameters["start_date"], "%Y-%m-%d"),
        end_date=datetime.strptime(parameters["end_date"], "%Y-%m-%d"),
        aoi=parameters["subset_wkt"],
        download_dir=parameters["download_dir"],
        netrc_path=parameters["netrc_path"]
    )
    safe_paths = downloader.run()

    selector = SubswathSelector(aoi_wkt=parameters["subset_wkt"], pol="VV")
    selected_subswath = selector.select_best_subswath(
        safe_paths=safe_paths,
        enforce_same_orbit=True,
        verbose=True
    )

    filtered_safe_paths = Filter_sar.filter_images(
        safe_paths,
        parameters["subset_wkt"],
        subswath=selected_subswath
    )

    filtered_json_path = os.path.join(parameters["download_dir"], "filtered_safe_paths.json")
    with open(filtered_json_path, "w", encoding="utf-8") as f:
        json.dump(filtered_safe_paths, f, indent=4)

    processor = PreprocessSentinel1(
        wkt_st=parameters["subset_wkt"],
        output_folder_path=parameters["output_folder_path"],
        export_intermediate=parameters["export_intermediate"],
        print_operators=parameters["print_operators"],
        subswath=selected_subswath
    )

    for filename, safe_path in filtered_safe_paths.items():
        processor.run(label=filename, safe_path=safe_path)

    print("\n--- Pipeline Complete: All images processed for VV and VH ---")


if __name__ == "__main__":
    main()
