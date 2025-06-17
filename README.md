
# 🧪 How to Use

Open Bash >> Run 

/Applications/Slicer.app/Contents/MacOS/Slicer --no-main-window --python-code "
  import sys
  sys.path.append('/Users/phd/Documents/slicer-stl-export')
  import slicer_stl_config as config
  exec(open('/Users/phd/Documents/slicer-stl-export/slicer_stl_export.py').read())
  main()
"

It will run slicer_stl_export.py using the parameters from slicer_stl_config.py.


# Slicer STL Export

This repository provides a Python utility to export a 3D segment from a segmentation node in 3D Slicer as an STL file, using the same logic as the GUI's "Export to Files" button. It is structured in modular functions and designed for reproducibility and clarity.

## 📦 Files Overview

- `slicer_stl_export.py` – Main pipeline script, with all logic structured into functions.
- `slicer_stl_config.py` – Stores all configurable parameters (volume name, export format, etc.).
- `.slicer` – Optional launcher file to be used directly inside 3D Slicer.
- `README.md` – This documentation file.

---

## 🔧 Configuration

Edit `slicer_stl_config.py` to define:

- `DICOM_FOLDER`: Folder path where the original DICOM data is stored.
- `SERIES_DESCRIPTION`: SeriesDescription string used to select the correct volume.
- `SEED_POINT_RAS`: A list with [x, y, z] coordinates for the segmentation seed.
- `OUTPUT_VOLUME_NAME`: Name of the intermediate filtered volume.
- `SEGMENTATION_NAME`: Name of the segmentation node.
- `SEGMENT_ID`: ID of the segment inside that segmentation node to export.
- `OUTPUT_FOLDER`: Full path to where the STL will be saved.
- `EXPORT_FORMAT`: One of `"STL"`, `"OBJ"`, `"VTK"`, `"PLY"`.
- `COORDINATE_SYSTEM`: Either `"RAS"` or `"LPS"` depending on compatibility.

---

## 🚀 Usage

1. Open 3D Slicer and load your scene or DICOM folder.
2. Modify `slicer_stl_config.py` with your data.
3. Run the pipeline from the Slicer Python Console or externally:

```bash
slicer --python slicer_stl_export.py
```

Or load via:

```
File > Run Script > slicer_stl_export.slicer
```

---

## 🧠 Function Overview (from slicer_stl_export.py)

All logic is encapsulated in the following functions:

- `import_dicom_series(dicom_folder, target_description)`  
  → Loads a scalar volume from a DICOM folder that matches a SeriesDescription.

- `create_seed_fiducial(seed_ras)`  
  → Places a fiducial seed point at the specified RAS coordinates.

- `apply_vesselness_filter(input_volume, seed_fiducial, output_name)`  
  → Applies the Vesselness Filtering module via Slicer's GUI backend using your seed and volume.

- `export_segment_to_stl(segmentation_node, segment_id, output_folder, format, coordsys)`  
  → Exports the selected segment to disk in STL or other formats using SegmentationsLogic.

- `main()`  
  → Runs the full pipeline in correct order using config values.

---

## ✅ Output

The script produces a `.stl` (or `.obj`, `.vtk`, etc.) file containing the vessel surface extracted from your segmentation node.

Files are named:
```
<SegmentationNodeName>.<SegmentID>.stl
```

---

## 📎 License

MIT
