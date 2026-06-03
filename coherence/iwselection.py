import os
import sys
from typing import Optional, Tuple, Dict, Any, Union, List



sys.path.append(os.environ.get("SNAP_PYTHON", os.path.expanduser("~/.snap/snap-python")))

from esa_snappy import ProductIO, GPF, HashMap


class SubswathSelector:

    SUBSWATHS = ("IW1", "IW2", "IW3")

    def __init__(self, aoi_wkt: str, pol: str = "VV"):
        self.aoi_wkt = aoi_wkt
        self.pol = pol

    @staticmethod
    def _normalize_safe_path(safe_path: str) -> str:
        if safe_path.lower().endswith(".safe") and os.path.isdir(safe_path):
            return os.path.join(safe_path, "manifest.safe")
        return safe_path

    @staticmethod
    def _intersection_area_pixels(manifest_path: str, aoi_wkt: str, subswath: str, pol: str) -> Tuple[Optional[str], int]:
      
        try:
            product = ProductIO.readProduct(manifest_path)

            metadata = product.getMetadataRoot().getElement("Abstracted_Metadata")
            rel_orbit = metadata.getAttribute("rel_orbit").getData().getElemString()

            split_params = HashMap()
            split_params.put("subswath", subswath)
            split_params.put("selectedPolarisations", pol)
            split_product = GPF.createProduct("TOPSAR-Split", split_params, product)

            subset_params = HashMap()
            subset_params.put("geoRegion", aoi_wkt)
            subset_product = GPF.createProduct("Subset", subset_params, split_product)

            w = subset_product.getSceneRasterWidth()
            h = subset_product.getSceneRasterHeight()

            return rel_orbit, int(w) * int(h)

        except Exception:
            return None, 0

    def select_best_subswath(self, safe_paths, enforce_same_orbit: bool = True, verbose: bool = True) -> str:
      
        
        if isinstance(safe_paths, dict):
            safe_list = list(safe_paths.values())
        else:
            safe_list = list(safe_paths)

        if not safe_list:
            raise ValueError("safe_paths is empty. Provide at least one SAFE/manifest path.")

        image_scores = []  

        for p in safe_list:
            manifest = self._normalize_safe_path(p)

            orbit_val = None
            areas = {}

            for sw in self.SUBSWATHS:
                orbit, area = self._intersection_area_pixels(
                    manifest_path=manifest,
                    aoi_wkt=self.aoi_wkt,
                    subswath=sw,
                    pol=self.pol,
                )
                areas[sw] = area
                if orbit is not None:
                    orbit_val = orbit

            best_sw = max(areas, key=areas.get)
            best_area = areas[best_sw]

            image_scores.append(
                {
                    "safe": p,
                    "orbit": orbit_val,
                    "best_subswath": best_sw,
                    "best_area": best_area,
                }
            )

            if verbose:
                base = os.path.basename(manifest)
                print(f"{base} -> best={best_sw} area={best_area} orbit={orbit_val}")

       
        best_image = max(image_scores, key=lambda x: x["best_area"])

        if verbose:
            print("\n==============================")
            print(" BEST SUBSWATH SELECTION:")
            print(f"SAFE: {best_image['safe']}")
            print(f"Orbit: {best_image['orbit']}")
            print(f"Selected subswath: {best_image['best_subswath']}")
            print(f"Intersection area (pixels): {best_image['best_area']}")
            print("==============================")

        return best_image["best_subswath"]
