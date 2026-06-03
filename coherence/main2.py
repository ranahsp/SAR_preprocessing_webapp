import json
import os
from datetime import datetime
from sentinel_downloader import SentinelDownloader
from interferometry import InterferometryProcessor
from iwselection import SubswathSelector
from filter_sar import Filter_sar


# 1. Load User Configuration
CONFIG_PATH = r"D:\earsel\580\config_input.json"
with open(CONFIG_PATH, 'r') as file:
    parameters = json.load(file)


# downloader = SentinelDownloader(
#     start_date=datetime.strptime(parameters["start_date"], "%Y-%m-%d"),
#     end_date=datetime.strptime(parameters["end_date"], "%Y-%m-%d"),
#     aoi=parameters["subset_wkt"],
#     download_dir=parameters["download_dir"],
#     netrc_path=parameters["netrc_path"]
# )


# safe_paths = downloader.run()
path=r"D:\earsel\580\images\safe_paths.json"

with open(path, 'r') as file2:
    safe_paths = json.load(file2)

selector = SubswathSelector(aoi_wkt=parameters["subset_wkt"])
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
filtered_safe_paths  = list(filtered_safe_paths.items())[::-1]
# Save the filtered paths to a new JSON for reference
filtered_json_path = os.path.join(parameters["download_dir"], "filtered_safe_paths.json")
with open(filtered_json_path, "w") as f:
    json.dump(filtered_safe_paths, f, indent=4)

pairs = [(filtered_safe_paths[i], filtered_safe_paths[i+1]) for i in range(len(filtered_safe_paths)-1)]
print (pairs)


interf_processor = InterferometryProcessor(
    subswath=selected_subswath,
    output_folder=parameters["output_folder_path"],
    wkt=parameters["subset_wkt"]
    # s1a_bursts=[3,6],
    # s1b_bursts=[3,6]
)

for idx, (master, slave) in enumerate(pairs, start=1):
    master_name, master_path = master
    slave_name, slave_path = slave
    
    master_date = master_path.split('_')[5][:8]
    slave_date = slave_path.split('_')[5][:8]
    
    output_name = f"interferogram_{idx}_{master_date}_vs_{slave_date}"

    interf_processor.run(
        master_path=master_path,
        slave_path=slave_path,
        output_base_name=output_name

        


    )



    
    print(f"Processed pair {idx}: {master_date} & {slave_date}")

print("All done.")