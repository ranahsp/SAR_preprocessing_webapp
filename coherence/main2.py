import json
import os
import argparse
from datetime import datetime
from pathlib import Path
from sentinel_downloader import SentinelDownloader
from interferometry import InterferometryProcessor
from iwselection import SubswathSelector
from filter_sar import Filter_sar


def load_parameters():
    parser = argparse.ArgumentParser(description="Run the coherence pipeline from a JSON config file.")
    parser.add_argument(
        "--config",
        default=str(Path(__file__).resolve().parents[1] / "tmp" / "coherence_config_input.json"),
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

    selector = SubswathSelector(aoi_wkt=parameters["subset_wkt"])
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
    filtered_safe_paths = list(filtered_safe_paths.items())[::-1]
    filtered_json_path = os.path.join(parameters["download_dir"], "filtered_safe_paths.json")
    with open(filtered_json_path, "w", encoding="utf-8") as f:
        json.dump(filtered_safe_paths, f, indent=4)

    pairs = [(filtered_safe_paths[i], filtered_safe_paths[i + 1]) for i in range(len(filtered_safe_paths) - 1)]
    print(pairs)

    interf_processor = InterferometryProcessor(
        subswath=selected_subswath,
        output_folder=parameters["output_folder_path"],
        wkt=parameters["subset_wkt"]
    )

    for idx, (master, slave) in enumerate(pairs, start=1):
        master_name, master_path = master
        slave_name, slave_path = slave

        master_date = Path(master_path).name.split('_')[5][:8]
        slave_date = Path(slave_path).name.split('_')[5][:8]
        output_name = f"interferogram_{idx}_{master_date}_vs_{slave_date}"

        interf_processor.run(
            master_path=master_path,
            slave_path=slave_path,
            output_base_name=output_name
        )
        print(f"Processed pair {idx}: {master_date} & {slave_date}")

    print("All done.")


if __name__ == "__main__":
    main()
