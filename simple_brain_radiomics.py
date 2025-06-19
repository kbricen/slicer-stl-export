# === simple_brain_radiomics.py ===
# Minimal script to extract radiomics features from a brain image and mask

from radiomics import featureextractor
import SimpleITK as sitk
import json

# Example files (replace with actual path if needed)
image_file = "brain_image.nii.gz"
mask_file = "brain_mask.nii.gz"

# Initialize extractor with default settings
extractor = featureextractor.RadiomicsFeatureExtractor()

# Load and extract
print("🔍 Extracting features from brain region...")
result = extractor.execute(image_file, mask_file)

# Save result
with open("brain_radiomics.json", "w") as f:
    json.dump({k: float(v) for k, v in result.items() if isinstance(v, (int, float))}, f, indent=2)

print("✅ Features saved to brain_radiomics.json")
