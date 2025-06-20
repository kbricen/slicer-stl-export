import SimpleITK as sitk
from radiomics import featureextractor
import os
import json
import csv

image_path = "/Users/phd/Documents/9/6 3D TOF 3SLAB FSPGR FS.nii.gz"
mask_path = "/Users/phd/Documents/9/VesselSegmentation-CircleOfWillisPatient-label.nii.gz"

image = sitk.ReadImage(image_path)
mask = sitk.ReadImage(mask_path)

# --- SAVE FUNCTION ---
def save_radiomics_output(result, basename="aneurysm_radiomics_output", save_json=True, save_csv=True):
    if save_json:
        with open(f"{basename}.json", "w") as f:
            # Convert ndarrays to lists
            clean_result = {
                k: (v.tolist() if hasattr(v, "tolist") else v)
                for k, v in result.items()
            }

            json.dump(clean_result, f, indent=4)

        print(f"💾 JSON saved: {basename}.json")

    if save_csv:
        with open(f"/Users/phd/Documents/9/{basename}.csv", "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Feature", "Value"])
            for k, v in result.items():
                writer.writerow([k, v])
        print(f"💾 CSV saved: /Users/phd/Documents/9/{basename}.csv")


# --- RUN EXTRACTOR ---
if not os.path.exists(image_path) or not os.path.exists(mask_path):
    print("❌ Image or mask file not found.")
else:
    extractor = featureextractor.RadiomicsFeatureExtractor()
    result = extractor.execute(image_path, mask_path)

    # Print to console
    print("\n📊 Radiomics Features:")
    for k, v in result.items():
        print(f"{k}: {v}")

    # Optional save
    save_radiomics_output(result)
