import os
import sys
import gc
sys.path.append(os.environ.get("SNAP_PYTHON", os.path.expanduser("~/.snap/snap-python")))
from esa_snappy import ProductIO, GPF, HashMap, jpy
System = jpy.get_type('java.lang.System')
Runtime = jpy.get_type('java.lang.Runtime')
java_int = jpy.get_type('java.lang.Integer')
GPF.getDefaultInstance().getOperatorSpiRegistry().loadOperatorSpis()
class InterferometryProcessor:
    def __init__(self, subswath, output_folder, wkt):
        self.subswath = subswath
        self.wkt = wkt
        self.output_folder = output_folder
        self.java_int = jpy.get_type('java.lang.Integer')
        GPF.getDefaultInstance().getOperatorSpiRegistry().loadOperatorSpis()

    def run(self, master_path, slave_path, output_base_name):
        # Process both polarizations for the given pair
        for pol in ["VV", "VH"]:
            print(f"--- Starting Coherence: {pol} polarization ---")
            
            master = ProductIO.readProduct(master_path)
            slave = ProductIO.readProduct(slave_path)

            orbit_params = HashMap()
            master_orbit = GPF.createProduct("Apply-Orbit-File", orbit_params, master)
            slave_orbit = GPF.createProduct("Apply-Orbit-File", orbit_params, slave)

            # Master Split
            split_params = HashMap()
            split_params.put("subswath", self.subswath)
            split_params.put("selectedPolarisations", pol)
            master_split = GPF.createProduct("TOPSAR-Split", split_params, master_orbit)

            # Slave Split
            split_params_s = HashMap()
            split_params_s.put("subswath", self.subswath)
            split_params_s.put("selectedPolarisations", pol)
            slave_split = GPF.createProduct("TOPSAR-Split", split_params_s, slave_orbit)

            bg_params = HashMap()
            bg_params.put("demName", "SRTM 3Sec")
            bg_params.put("resamplingType", "BILINEAR_INTERPOLATION")
            bg_params.put("maskOutAreaWithoutElevation", True)
            coregistered = GPF.createProduct("Back-Geocoding", bg_params, [slave_split, master_split])

            interf_params = HashMap()
            interf_params.put("subtractFlatEarthPhase", True)
            interf_params.put("subtractTopographicPhase", True)
            interf_params.put("demName", "SRTM 3Sec")
            interf_params.put("flatEarthPolynomialDegree", 5)
            interf_params.put("includeCoherence", True)
            interf_params.put("cohWinAzimuth", 3)
            interf_params.put("cohWinRange", 10)
            interf_params.put("squarePixel", True)
            interferogram = GPF.createProduct("Interferogram", interf_params, coregistered)

            deburst = GPF.createProduct("TOPSAR-Deburst", HashMap(), interferogram)

            tc_params = HashMap()
            tc_params.put("demName", "SRTM 3Sec")
            tc_params.put("pixelSpacingInMeter", 90.0)
            tc_params.put("mapProjection", "WGS84(DD)")
            tc_params.put("maskOutAreaWithoutElevation", True)
            tc_params.put("outputComplex", False)
            tc_params.put("outputIntensity", True)
            tc_params.put("demResamplingMethod", "BILINEAR_INTERPOLATION")
            tc_params.put("imgResamplingMethod", "BILINEAR_INTERPOLATION")
            terrain_corrected = GPF.createProduct("Terrain-Correction", tc_params, deburst)

            # Subset to AOI and select Coherence Band
            for band_name in list(terrain_corrected.getBandNames()):
                if band_name.startswith('Intensity_ifg_'):
                    terrain_corrected.removeBand(terrain_corrected.getBand(band_name))

            coherence_band_name = None
            for band_name in terrain_corrected.getBandNames():
                if "coh_" in band_name or "coh" in band_name.lower():
                    coherence_band_name = band_name
                    break
            subset_params = HashMap()
            subset_params.put("geoRegion", self.wkt)
            subset_params.put("bandNames", coherence_band_name)
            subset_params.put("copyMetadata", True)
            subset = GPF.createProduct("Subset", subset_params, terrain_corrected)

            final_output = os.path.join(self.output_folder, f"{output_base_name}_{pol}.tif")
            ProductIO.writeProduct(subset, final_output, "GeoTIFF")
            
            # Clean up memory
            subset.dispose()
            master.dispose()
            slave.dispose()
            System.gc()
