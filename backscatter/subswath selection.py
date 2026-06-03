import os
import sys
import json
sys.path.append(os.environ.get("SNAP_PYTHON", os.path.expanduser("~/.snap/snap-python")))

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


# ---- READ SAFE PATHS ----
with open(r"C:/polimi/thesis/CALABRIA/S1_Batch2/safe_paths.json", "r") as f:
    safe_paths_dict = json.load(f)

safe_files = list(safe_paths_dict.values())

# ---- AOI ----
aoi_wkt = "POLYGON((15.909289166000065 37.92512127600003, 15.788710796000032 37.91140670800007, 15.751285712000026 37.934545558000025, 15.658897939000042 37.982728063000025, 15.689516652000066 38.25393487100007, 16.182438018000028 38.19364022000008, 16.055757319000065 37.93693152000003, 15.909289166000065 37.92512127600003))"


# ---- COMPUTE BEST AOI INTERSECTION PER IMAGE ----
image_scores = []  # list of dicts: {safe, orbit, best_subswath, best_area}

for safe_path in safe_files:
    areas = {}
    orbit_val = None

    for sw in ["IW1", "IW2", "IW3"]:
        orbit, area = intersection_area_pixels(safe_path, aoi_wkt, sw, pol="VV")
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


# ---- GET THE IMAGE WITH MAX AOI INTERSECTION ----
best_image = max(image_scores, key=lambda x: x["best_area"])

print("\n==============================")
print("IMAGE WITH MAX AOI INTERSECTION:")
print(f"SAFE: {best_image['safe']}")
print(f"Orbit: {best_image['orbit']}")
print(f"Best subswath: {best_image['best_subswath']}")
print(f"Intersection area (pixels): {best_image['best_area']}")
print("==============================")
