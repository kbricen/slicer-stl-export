# Project Structure Summary

## 📋 Overview

**Slicer STL Export** is a Python-based automation tool for 3D Slicer that processes medical imaging data (DICOM) to extract and export vascular structures as 3D surface models (STL files). The pipeline performs vessel segmentation using vesselness filtering and provides automated export capabilities for both 3D meshes and volumetric data.

**Primary Use Case**: Automated extraction of Circle of Willis vessels from brain MRI TOF (Time of Flight) sequences for medical visualization, surgical planning, and radiomics analysis.

---

## 🗂️ File Structure

```
slicer-stl-export/
├── slicer_stl_export.py        # Main pipeline orchestration and processing functions
├── slicer_stl_config.py        # Configuration parameters for the pipeline
├── simple_brain_radiomics.py   # Radiomics feature extraction (post-processing)
├── requirements.txt            # Python dependencies
├── setup_git_auth.sh          # Git authentication setup script
├── README.md                   # User documentation and usage instructions
├── .gitignore                 # Git ignore patterns
└── STRUCTURE.md               # This file - project structure documentation
```

---

## 📦 Core Components

### 1. **slicer_stl_export.py** (Main Pipeline)

The central processing script containing all pipeline logic. Designed to run within 3D Slicer's Python environment.

#### Key Functions:

- **`import_dicom_series(dicom_folder, target_description)`**
  - Loads DICOM series matching a specific SeriesDescription
  - Returns: `vtkMRMLScalarVolumeNode` or `None`

- **`create_seed_fiducial(seed_ras)`**
  - Creates a fiducial marker at specified RAS coordinates
  - Used as input for vessel segmentation algorithms
  - Returns: `vtkMRMLMarkupsFiducialNode`

- **`apply_vesselness_filter(input_volume, seed_fiducial, output_name)`**
  - Applies Frangi vesselness filtering to enhance tubular structures
  - Configurable diameter range (0.5-3.0 mm) and suppression parameters
  - Returns: Filtered `vtkMRMLScalarVolumeNode`

- **`fill_segmentation_from_volume(segmentation_node, segment_id, volume_node, threshold_min, threshold_max)`**
  - Performs intensity-based thresholding to create initial segmentation
  - Default threshold: 0.8-1.0 (normalized vesselness response)

- **`keep_largest_island_in_segment(segmentationNode, segmentID, volumeNode)`**
  - Removes disconnected components, keeping only the largest connected island
  - Uses Segment Editor's Islands effect

- **`keep_islands_by_ijk_coordinates(segmentationNode, segmentID, ijk_coords_list, volumeNode)`**
  - Advanced island selection based on user-specified voxel coordinates
  - Converts IJK (voxel) coordinates to RAS (world) coordinates
  - Keeps only islands containing the specified points

- **`export_segment_to_stl(segmentation_node, segment_id, output_folder, format, coordsys)`**
  - Exports segmentation as 3D surface mesh
  - Supports: STL, OBJ, VTK, PLY formats
  - Coordinate systems: RAS or LPS

- **`export_segmentation_and_volume_as_nifti(segmentation_node, volume_node, image_path, label_path)`**
  - Exports paired volume + labelmap as NIfTI files
  - Useful for radiomics analysis or machine learning pipelines

- **`main()`**
  - Orchestrates the entire pipeline in correct sequence
  - Reads configuration from `slicer_stl_config.py`
  - Executes all steps from DICOM import to final export

---

### 2. **slicer_stl_config.py** (Configuration)

Centralized parameter storage for reproducible processing.

#### Configuration Parameters:

| Parameter | Type | Description | Example Value |
|-----------|------|-------------|---------------|
| `DICOM_FOLDER` | `str` | Path to DICOM directory | `"/path/to/DICOM"` |
| `SERIES_DESCRIPTION` | `str` | DICOM SeriesDescription to match | `"3D TOF 3SLAB FSPGR FS"` |
| `SEED_POINT_RAS` | `list[float]` | RAS coordinates for seed point | `[2.5, 30.0, 42.0]` |
| `OUTPUT_VOLUME_NAME` | `str` | Name for filtered volume node | `"FilteredVesselsPython"` |
| `SEGMENTATION_NAME` | `str` | Name for segmentation node | `"VesselSegmentation"` |
| `SEGMENT_ID` | `str` | ID of segment to export | `"VesselSegmentation_Segment_1"` |
| `OUTPUT_FOLDER` | `str` | Directory for exported files | `"/path/to/output"` |
| `EXPORT_FORMAT` | `str` | Output mesh format | `"STL"` (or OBJ, VTK, PLY) |
| `COORDINATE_SYSTEM` | `str` | Coordinate system for export | `"RAS"` or `"LPS"` |
| `SELECTED_VOXELS_TO_KEEP` | `list[list[int]]` | IJK coordinates of islands to keep | `[[282, 220, 40]]` |

---

### 3. **simple_brain_radiomics.py** (Post-Processing)

Standalone script for extracting radiomics features from segmented vessels.

#### Functionality:
- Uses PyRadiomics library for feature extraction
- Inputs: NIfTI image + mask pair
- Outputs: JSON and CSV files with quantitative features
- Features include:
  - First-order statistics (mean, variance, skewness, etc.)
  - Shape descriptors (volume, surface area, sphericity)
  - Texture features (GLCM, GLRLM, GLSZM)

---

## 🔄 Pipeline Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. DICOM Import                                             │
│    • Load specific series by SeriesDescription              │
│    • Create temporary DICOM database                        │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Seed Point Creation                                      │
│    • Place fiducial marker at RAS coordinates               │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Vesselness Filtering                                     │
│    • Apply Frangi filter with seed guidance                 │
│    • Parameters: diameter 0.5-3.0mm, suppress blobs/plates │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Segmentation Creation                                    │
│    • Threshold filtered volume (0.8-1.0)                    │
│    • Create binary segment                                  │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Island Selection                                         │
│    • Keep islands at specified IJK coordinates              │
│    • Remove disconnected artifacts                          │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Surface Generation                                       │
│    • Create closed surface representation                   │
└────────────────┬────────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Export                                                   │
│    • STL/OBJ mesh export                                    │
│    • NIfTI volume + labelmap export                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔧 Dependencies

### Python Packages (requirements.txt)

| Package | Version | Purpose |
|---------|---------|---------|
| `simpleitk` | 2.5.2 | Medical image I/O and processing |
| `pyradiomics` | (local) | Radiomics feature extraction |
| `numpy` | 2.0.2 | Numerical operations |
| `PyWavelets` | 1.6.0 | Wavelet transforms for texture analysis |
| `ruamel.yaml` | 0.18.14 | YAML configuration parsing |
| `docopt` | 0.6.2 | Command-line argument parsing |
| `pykwalify` | 1.8.0 | Schema validation |
| `python-dateutil` | 2.9.0 | Date/time utilities |
| `six` | 1.17.0 | Python 2/3 compatibility |

### External Dependencies

- **3D Slicer** (5.4.0+): Medical image visualization and processing platform
- **Slicer Modules**:
  - `VesselnessFiltering`: Frangi filter implementation
  - `Segmentations`: Segmentation logic and export
  - `DICOMLib`: DICOM import utilities

---

## 🚀 Usage Patterns

### Running on macOS

```bash
/Applications/Slicer.app/Contents/MacOS/Slicer --python-code "import sys; \
sys.path.append('/path/to/slicer-stl-export'); \
import slicer_stl_config as config; \
exec(open('/path/to/slicer-stl-export/slicer_stl_export.py').read()); \
main()"
```

### Running on Windows

```cmd
"C:\Program Files\Slicer 5.4.0\Slicer.exe" --no-main-window --python-code ^
"import sys; sys.path.append('C:/path/to/slicer-stl-export'); ^
import slicer_stl_config as config; ^
exec(open('C:/path/to/slicer-stl-export/slicer_stl_export.py').read()); ^
main()"
```

### Configuration Workflow

1. Edit `slicer_stl_config.py` with your parameters
2. Run the pipeline through Slicer's Python interpreter
3. Outputs will be saved to `OUTPUT_FOLDER`:
   - `<SegmentationName>.<SegmentID>.stl` - 3D mesh
   - `circle_image.nii.gz` - Original filtered volume
   - `circle_segmentation.nii.gz` - Binary segmentation mask

---

## 📊 Output Files

### Primary Outputs

1. **STL Mesh**: `VesselSegmentation.VesselSegmentation_Segment_1.stl`
   - 3D surface model of segmented vessels
   - Ready for 3D printing, visualization, or surgical planning

2. **NIfTI Volume**: `circle_image.nii.gz`
   - Vesselness-filtered volume in NIfTI format
   - Preserves original intensity information

3. **NIfTI Labelmap**: `circle_segmentation.nii.gz`
   - Binary segmentation mask
   - Aligned with original image geometry

### Optional Outputs (via radiomics script)

4. **Radiomics JSON**: `aneurysm_radiomics_output.json`
   - 100+ quantitative features describing vessel morphology and texture

5. **Radiomics CSV**: `aneurysm_radiomics_output.csv`
   - Same features in spreadsheet format for analysis

---

## 🎯 Design Principles

1. **Modularity**: Each function performs a single, well-defined task
2. **Reproducibility**: All parameters externalized to config file
3. **Automation**: Minimal user interaction after configuration
4. **Extensibility**: Easy to add new processing steps or export formats
5. **Slicer Integration**: Uses native Slicer APIs and modules for reliability

---

## 🔍 Key Technical Details

### Coordinate Systems

- **RAS (Right-Anterior-Superior)**: Slicer's native coordinate system
- **IJK (Image)**: Voxel coordinates in the volume array
- **LPS (Left-Posterior-Superior)**: Alternative medical imaging standard

The pipeline handles conversions between these systems transparently.

### Segmentation Strategy

1. **Vesselness Enhancement**: Highlights tubular structures (vessels)
2. **Thresholding**: Converts enhanced image to binary mask
3. **Island Analysis**: Separates disconnected components
4. **Selective Retention**: Keeps only clinically relevant structures

### Export Mechanisms

- **Mesh Export**: Uses `ExportSegmentsClosedSurfaceRepresentationToFiles()`
- **Volume Export**: Uses `slicer.util.saveNode()` for NIfTI format
- **Labelmap Creation**: Converts segmentation to volume representation

---

## 📝 License

DFG 1294 "Data Assimilation"

---

## 🔗 Related Files

- **README.md**: User-facing documentation with setup instructions
- **.gitignore**: Excludes temporary files and large data directories
- **setup_git_auth.sh**: Helper script for repository authentication

---

*This structure summary provides a comprehensive overview of the slicer-stl-export project architecture, components, and workflows.*
