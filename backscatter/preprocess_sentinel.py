import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from snap_python import ensure_esa_snappy

ensure_esa_snappy()
import esa_snappy
from esa_snappy import ProductIO, GPF, HashMap, jpy

class PreprocessSentinel1:
    def __init__(self, wkt_st, subswath, output_folder_path, export_intermediate=False, print_operators=False):
        self.ProductIO = ProductIO
        self.GPF = GPF
        self.HashMap = HashMap
        self.jpy = jpy
        self.ProductUtils = jpy.get_type('org.esa.snap.core.util.ProductUtils')
        self.wkt_st = wkt_st
        self.subswath = subswath
        self.output_folder_path = output_folder_path
        self.export_intermediate = export_intermediate
        self.print_operators = print_operators

    def run(self, label, safe_path):
        label_clean = os.path.splitext(label)[0].replace(" ", "_")
        slc_product = self.ProductIO.readProduct(safe_path)

        # Process both polarizations
        for pol in ["VV", "VH"]:
            print(f"--- Processing {label_clean} in {pol} polarization ---")
            
            parameters = self.HashMap()
            parameters.put("Apply-Orbit-File", True)
            orbit_corrected = self.GPF.createProduct("Apply-Orbit-File", parameters, slc_product)

            parameters1 = self.HashMap()
            parameters1.put("removeThermalNoise", True)
            thermal_removed = self.GPF.createProduct("ThermalNoiseRemoval", parameters1, orbit_corrected)

            parameters2 = self.HashMap()
            parameters2.put("subswath", self.subswath)
            parameters2.put("selectedPolarisations", pol)
            split_product = self.GPF.createProduct("TOPSAR-Split", parameters2, thermal_removed)

            parameters3 = self.HashMap()
            parameters3.put("outputBetaBand", True)
            parameters3.put("sourceBands", f"Intensity_{self.subswath}_{pol}")
            parameters3.put("selectedPolarisations", pol)
            calibrated_product = self.GPF.createProduct("Calibration", parameters3, split_product)

            debursted_product = self.GPF.createProduct("TOPSAR-Deburst", self.HashMap(), calibrated_product)

            java_int = self.jpy.get_type('java.lang.Integer')
            parameters5 = self.HashMap()
            parameters5.put("nRgLooks", java_int(3))
            parameters5.put("nAzLooks", java_int(3))
            parameters5.put("sourceBands", f"Beta0_{self.subswath}_{pol}")
            multilooked_product = self.GPF.createProduct("Multilook", parameters5, debursted_product)

            speckle_filtered_product = self.GPF.createProduct("Speckle-Filter", self.HashMap(), multilooked_product)

            parameters7 = self.HashMap()
            parameters7.put("sourceBands", f"Beta0_{self.subswath}_{pol}")
            parameters7.put("demName", "SRTM 3Sec")
            flattened_product = self.GPF.createProduct("Terrain-Flattening", parameters7, speckle_filtered_product)

            parameter8 = self.HashMap()
            parameter8.put("demName", "SRTM 3Sec")
            parameter8.put("pixelSpacingInMeter", 10.0)
            parameter8.put("sourceBands", f"Gamma0_{self.subswath}_{pol}")
            terrain_corrected_product = self.GPF.createProduct("Terrain-Correction", parameter8, flattened_product)

            parameters9 = self.HashMap()
            parameters9.put("geoRegion", self.wkt_st)
            parameters9.put("sourceBands", f"Gamma0_{self.subswath}_{pol}")
            subset_product = self.GPF.createProduct("Subset", parameters9, terrain_corrected_product)

            parameters10 = self.HashMap()
            parameters10.put("sourceBands", f"Gamma0_{self.subswath}_{pol}")
            dB_product = self.GPF.createProduct("LinearToFromdB", parameters10, subset_product)

            output_path = os.path.join(self.output_folder_path, f"{label_clean}_{pol}_dB.tif")
            self.ProductIO.writeProduct(dB_product, output_path, "GeoTIFF")
            print(f"Exported: {output_path}")
