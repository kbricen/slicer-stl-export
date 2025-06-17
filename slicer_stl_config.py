
# === slicer_stl_config.py ===

# Folder path where the original DICOM data is stored
DICOM_FOLDER = "/Users/phd/Documents/9/Anonym Images/Gehirn MRT Pre-OP 31-01-2025/DICOM"

# SeriesDescription string used to select the correct volume
SERIES_DESCRIPTION = "3D TOF 3SLAB FSPGR FS"

# A list with [x, y, z] coordinates for the segmentation seed
SEED_POINT_RAS = [2.5, 30.0, 42.0]

# Name of the intermediate filtered volume
OUTPUT_VOLUME_NAME = "FilteredVesselsPython"

# Name of the segmentation node
SEGMENTATION_NAME = "VesselSegmentation"

# ID of the segment inside that segmentation node to export
SEGMENT_ID = "VesselSegmentation_Segment_1"

# Full path to where the STL will be saved
OUTPUT_FOLDER = "/Users/phd/Documents/9/Anonym Images"

# Export format: one of "STL", "OBJ", "VTK", "PLY"
EXPORT_FORMAT = "STL"

# Coordinate system: either "RAS" or "LPS"
COORDINATE_SYSTEM = "RAS"
