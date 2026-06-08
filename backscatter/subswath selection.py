import os
import json
import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from snap_python import ensure_esa_snappy

ensure_esa_snappy()
from esa_snappy import ProductIO, GPF, HashMap


def intersection_area_pixels(safe_path, aoi_wkt, subswath, pol="VV"):
    try:
        if safe_path.lower().endswith(".safe") and os.path.isdir(safe_path):
            safe_path = os.path.join(safe_path, "manifest.safe")

        product = ProductIO.readProduct(safe_path)

        metadata = product.getMetadataRoot().getElement('Abstracted_Metadata')
        rel_orbit = metadata.getAttribute('rel_orbit').getData().getElemString()

        split_params = HashMap()
        split_params.put("subswath", subswath)
        split_params.put("selectedPolarisations", pol)
        split_product = GPF.createProduct("TOPSAR-Split", split_params, product)

        subset_params = HashMap()
        subset_params.put("geoRegion", aoi_wkt)
        subset_product = GPF.createProduct("Subset", subset_params, split_product)

        w = subset_product.getSceneRasterWidth()
        h = subset_product.getSceneRasterHeight()
        return rel_orbit, w * h

    except Exception:
        return None, 0


def parse_args():
    parser = argparse.ArgumentParser(description="Select the Sentinel-1 subswath with the largest AOI intersection.")
    parser.add_argument("--safe-paths-json", required=True, help="Path to safe_paths.json.")
    parser.add_argument("--wkt", required=True, help="AOI polygon WKT.")
    return parser.parse_args()


def main():
    args = parse_args()
    with open(args.safe_paths_json, "r", encoding="utf-8") as f:
        safe_paths_dict = json.load(f)

    safe_files = list(safe_paths_dict.values())
    image_scores = []

    for safe_path in safe_files:
        areas = {}
        orbit_val = None

        for sw in ["IW1", "IW2", "IW3"]:
            orbit, area = intersection_area_pixels(safe_path, args.wkt, sw, pol="VV")
            areas[sw] = area
            if orbit:
                orbit_val = orbit

        best_sw = max(areas, key=areas.get)
        best_area = areas[best_sw]

        image_scores.append({
            "safe": safe_path,
            "orbit": orbit_val,
            "best_subswath": best_sw,
            "best_area": best_area
        })

        print(f"{os.path.basename(safe_path)} -> best={best_sw} area={best_area} orbit={orbit_val}")

    best_image = max(image_scores, key=lambda x: x["best_area"])

    print("\n==============================")
    print("IMAGE WITH MAX AOI INTERSECTION:")
    print(f"SAFE: {best_image['safe']}")
    print(f"Orbit: {best_image['orbit']}")
    print(f"Best subswath: {best_image['best_subswath']}")
    print(f"Intersection area (pixels): {best_image['best_area']}")
    print("==============================")


if __name__ == "__main__":
    main()
