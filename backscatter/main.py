import json
import os
from datetime import datetime
from sentinel_downloader import SentinelDownloader
from preprocess_sentinel import PreprocessSentinel1
from iwselection import SubswathSelector
from filter_sar import Filter_sar

# 1. Load User Configuration
CONFIG_PATH = r"D:\earsel\580\config_input.json"
with open(CONFIG_PATH, 'r') as file:
    parameters = json.load(file)

# 2. Download Images
downloader = SentinelDownloader(
    start_date=datetime.strptime(parameters["start_date"], "%Y-%m-%d"),
    end_date=datetime.strptime(parameters["end_date"], "%Y-%m-%d"),
    aoi=parameters["subset_wkt"],
    download_dir=parameters["download_dir"],
    netrc_path=parameters["netrc_path"]
)

# This automatically runs download and returns the dictionary of paths
# It also saves safe_paths.json inside the download_dir automatically
safe_paths = downloader.run()

# 3. Select Best Subswath
selector = SubswathSelector(aoi_wkt=parameters["subset_wkt"], pol="VV")
selected_subswath = selector.select_best_subswath(
    safe_paths=safe_paths,
    enforce_same_orbit=True,
    verbose=True
)

# 4. Filter SAR Images by Orbit
# This uses the output from the selector/downloader
filtered_safe_paths = Filter_sar.filter_images(
    safe_paths, 
    parameters["subset_wkt"], 
    subswath=selected_subswath
)

# Save the filtered paths to a new JSON for reference
filtered_json_path = os.path.join(parameters["download_dir"], "filtered_safe_paths.json")
with open(filtered_json_path, "w") as f:
    json.dump(filtered_safe_paths, f, indent=4)

# 5. Preprocessing (VV and VH)
processor = PreprocessSentinel1(
    wkt_st=parameters["subset_wkt"],
    output_folder_path=parameters["output_folder_path"],
    export_intermediate=parameters["export_intermediate"],
    print_operators=parameters["print_operators"],
    subswath=selected_subswath  # Using the automatically detected subswath
)

for filename, safe_path in filtered_safe_paths.items():
    processor.run(label=filename, safe_path=safe_path)

print("\n--- Pipeline Complete: All images processed for VV and VH ---")