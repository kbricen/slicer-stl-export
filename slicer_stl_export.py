
# === slicer_stl_export.py ===

from DICOMLib import DICOMUtils
import pydicom
import os
import slicer
import vtk

from slicer_stl_config import (
    DICOM_FOLDER,
    SERIES_DESCRIPTION,
    SEED_POINT_RAS,
    OUTPUT_VOLUME_NAME,
    SEGMENTATION_NAME,
    SEGMENT_ID,
    OUTPUT_FOLDER,
    EXPORT_FORMAT,
    COORDINATE_SYSTEM,
    SELECTED_VOXELS_TO_KEEP
)

def import_dicom_series(dicom_folder, target_description):
    with DICOMUtils.TemporaryDICOMDatabase() as db:
        DICOMUtils.importDicom(dicom_folder, db)
        patientUIDs = db.patients()
        for patientUID in patientUIDs:
            studies = db.studiesForPatient(patientUID)
            for studyUID in studies:
                seriesUIDs = db.seriesForStudy(studyUID)
                for seriesUID in seriesUIDs:
                    filePaths = db.filesForSeries(seriesUID)
                    if not filePaths:
                        continue
                    ds = pydicom.dcmread(filePaths[0], stop_before_pixels=True)
                    if getattr(ds, 'SeriesDescription', '').strip() == target_description:
                        loadedNodeIDs = DICOMUtils.loadSeriesByUID([seriesUID])
                        for nodeID in loadedNodeIDs:
                            node = slicer.mrmlScene.GetNodeByID(nodeID)
                            if node.IsA("vtkMRMLScalarVolumeNode"):
                                return node
    return None

def create_seed_fiducial(seed_ras):
    fiducialNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode", "SeedFiducial")
    fiducialNode.RemoveAllControlPoints()
    fiducialNode.AddControlPoint(seed_ras[0], seed_ras[1], seed_ras[2])
    return fiducialNode

def apply_vesselness_filter(input_volume, seed_fiducial, output_name):
    outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", output_name)
    slicer.util.selectModule("VesselnessFiltering")
    vf_gui = slicer.modules.vesselnessfiltering.widgetRepresentation().self()
    vf_gui.inputVolumeNodeSelector.setCurrentNode(input_volume)
    vf_gui.outputVolumeNodeSelector.setCurrentNode(outputVolume)
    vf_gui.seedFiducialsNodeSelector.setCurrentNode(seed_fiducial)
    vf_gui.minimumDiameterSpinBox.setValue(0.5)
    vf_gui.maximumDiameterSpinBox.setValue(3.0)
    vf_gui.suppressBlobsSlider.setValue(0.4)
    vf_gui.suppressPlatesSlider.setValue(0.6)
    vf_gui.onStartButtonClicked()
    return outputVolume

def fill_segmentation_from_volume(segmentation_node, segment_id, volume_node, threshold_min=0.8, threshold_max=1.0):
    # Setup Segment Editor
    editorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
    editorNode.SetAndObserveSegmentationNode(segmentation_node)
    editorNode.SetAndObserveSourceVolumeNode(volume_node)

    editorWidget = slicer.qMRMLSegmentEditorWidget()
    editorWidget.setMRMLScene(slicer.mrmlScene)
    editorWidget.setMRMLSegmentEditorNode(editorNode)

    editorWidget.setCurrentSegmentID(segment_id)
    editorWidget.setActiveEffectByName("Threshold")
    effect = editorWidget.activeEffect()
    effect.setParameter("MinimumThreshold", str(threshold_min))
    effect.setParameter("MaximumThreshold", str(threshold_max))
    effect.self().onApply()

    editorWidget = None  # cleanup

def keep_largest_island_in_segment(segmentationNode, segmentID, volumeNode=None):
    """
    Applies the 'Islands' effect in Segment Editor to keep the largest island in a segment.

    Parameters:
        segmentationNode (vtkMRMLSegmentationNode): the node containing the segment
        segmentID (str): ID of the segment to process (not the name)
        volumeNode (vtkMRMLScalarVolumeNode, optional): source volume, needed if using intensity-based effects
    """
    # Create and configure Segment Editor
    editorWidget = slicer.qMRMLSegmentEditorWidget()
    editorWidget.setMRMLScene(slicer.mrmlScene)
    
    editorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
    editorWidget.setSegmentEditorNode(editorNode)
    editorWidget.setSegmentationNode(segmentationNode)
    if volumeNode:
        editorWidget.setSourceVolumeNode(volumeNode)

    # Apply Islands effect
    editorWidget.setActiveSegmentID(segmentID)
    editorWidget.setActiveEffectByName("Islands")
    effect = editorWidget.activeEffect()
    effect.setParameter("Operation", "KEEP_LARGEST_ISLAND")
    effect.setParameter("MinimumSize", "0")  # Optional
    effect.self().apply()

    print(f"✅ Largest island kept in segment: {segmentID}")

def export_segment_to_stl(segmentation_node, segment_id, output_folder, format="STL", coordsys="RAS"):
    ids = vtk.vtkStringArray()
    ids.InsertNextValue(segment_id)
    slicer.modules.segmentations.logic().ExportSegmentsClosedSurfaceRepresentationToFiles(
        output_folder,
        segmentation_node,
        ids,
        format,
        coordsys,
        False
    )
    print(f"✅ Exported segment '{segment_id}' to {output_folder}")

def export_segmentation_and_volume_as_nifti(segmentation_node, volume_node, image_path, label_path):
    

    # Export segmentation to labelmap
    labelmap_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode", "LabelmapFromSegmentation")
    slicer.modules.segmentations.logic().ExportVisibleSegmentsToLabelmapNode(segmentation_node, labelmap_node, volume_node)

    # Save the volume image
    slicer.util.saveNode(volume_node, image_path)

    # Save the label map (segmentation)
    slicer.util.saveNode(labelmap_node, label_path)

    print(f"✅ Saved image to: {image_path}")
    print(f"✅ Saved labelmap to: {label_path}")


def keep_islands_by_coordinates(segmentationNode, segmentID, coordsRAS, referenceVolume):
    """
    Keeps islands in a segment that contain the specified RAS coordinates.

    Parameters:
        segmentationNode: vtkMRMLSegmentationNode
        segmentID: str - ID of the segment
        coordsRAS: list of [x, y, z] coordinates
        referenceVolume: vtkMRMLScalarVolumeNode - the reference volume for transformation
    """
    import numpy as np

    # Set up Segment Editor and Islands effect
    editorWidget = slicer.qMRMLSegmentEditorWidget()
    editorWidget.setMRMLScene(slicer.mrmlScene)

    editorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
    editorWidget.setSegmentEditorNode(editorNode)
    editorWidget.setSegmentationNode(segmentationNode)
    editorWidget.setSourceVolumeNode(referenceVolume)
    editorWidget.setActiveSegmentID(segmentID)

    editorWidget.setActiveEffectByName("Islands")
    effect = editorWidget.activeEffect()
    effect.setParameter("Operation", "SPLIT_ISLANDS")
    effect.setParameter("MinimumSize", "0")
    effect.self().apply()

    # Collect island IDs based on RAS positions
    selected_ids = set()
    labelmapNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLLabelMapVolumeNode")

    ras2ijk = vtk.vtkMatrix4x4()
    referenceVolume.GetRASToIJKMatrix(ras2ijk)

    for ras in coordsRAS:
        ijk = [0, 0, 0, 1]
        ras2ijk.MultiplyPoint(list(ras) + [1], ijk)
        ijk_int = tuple(int(round(c)) for c in ijk[:3])

        labelmapArray = slicer.util.arrayFromVolume(labelmapNode)
        try:
            label = labelmapArray[ijk_int[2], ijk_int[1], ijk_int[0]]
            selected_ids.add(label)
        except IndexError:
            print(f"⚠️ Coordinate {ras} is outside of labelmap bounds.")

    if not selected_ids:
        print("❌ No valid islands found at provided coordinates.")
        return

    # Convert to string for Islands effect
    selected_ids = [str(i) for i in selected_ids if i != 0]
    print(f"✅ Found island labels to keep: {selected_ids}")

    # Apply KEEP_SELECTED_ISLANDS
    effect.setParameter("Operation", "KEEP_SELECTED_ISLANDS")
    effect.setParameter("SelectedIslandIds", ",".join(selected_ids))
    effect.self().apply()
    print(f"✅ Kept islands from coordinates in segment: {segmentID}")

def keep_islands_by_ijk_coordinates(segmentationNode, segmentID, ijk_coords_list, volumeNode):
    """
    Given a list of IJK voxel coordinates, convert to RAS, find which islands they belong to,
    and apply the 'KEEP_SELECTED_ISLANDS' operation on those island labels.

    Parameters:
        segmentationNode (vtkMRMLSegmentationNode): Segmentation node
        segmentID (str): ID of the segment
        ijk_coords_list (list of [i,j,k]): List of voxel coordinates
        volumeNode (vtkMRMLScalarVolumeNode): Reference volume (used for RAS transform and label mapping)
    """
    import numpy as np
    import vtk

    # Step 1: Convert IJK to RAS
    ijkToRAS = vtk.vtkMatrix4x4()
    volumeNode.GetIJKToRASMatrix(ijkToRAS)

    coordsRAS = []
    for ijk in ijk_coords_list:
        ras_hom = [0, 0, 0, 0]
        ijk_hom = list(ijk) + [1]
        ijkToRAS.MultiplyPoint(ijk_hom, ras_hom)
        coordsRAS.append(ras_hom[:3])

    print(f"🔁 Converted IJK to RAS:\n{coordsRAS}")

    # Step 2: Use Segment Editor Islands effect
    editorWidget = slicer.qMRMLSegmentEditorWidget()
    editorWidget.setMRMLScene(slicer.mrmlScene)

    editorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
    editorWidget.setSegmentEditorNode(editorNode)
    editorWidget.setSegmentationNode(segmentationNode)
    editorWidget.setSourceVolumeNode(volumeNode)
    editorWidget.setActiveSegmentID(segmentID)

    # Split islands to label them
    editorWidget.setActiveEffectByName("Islands")
    effect = editorWidget.activeEffect()
    effect.setParameter("Operation", "SPLIT_ISLANDS")
    effect.setParameter("MinimumSize", "0")
    effect.self().apply()

    # Step 3: Identify which island label each RAS point is in
    labelmapNode = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLLabelMapVolumeNode")
    ras2ijk = vtk.vtkMatrix4x4()
    volumeNode.GetRASToIJKMatrix(ras2ijk)
    labelmapArray = slicer.util.arrayFromVolume(labelmapNode)

    island_ids = set()
    for ras in coordsRAS:
        ijk = [0, 0, 0, 1]
        ras2ijk.MultiplyPoint(ras + [1], ijk)
        ijk_int = tuple(int(round(c)) for c in ijk[:3])
        try:
            label = labelmapArray[ijk_int[2], ijk_int[1], ijk_int[0]]
            if label > 0:
                island_ids.add(label)
        except IndexError:
            print(f"⚠️ RAS {ras} → IJK {ijk_int} is out of bounds.")

    if not island_ids:
        print("❌ No valid islands found for given coordinates.")
        return

    # Step 4: Keep only selected islands
    effect.setParameter("Operation", "KEEP_SELECTED_ISLANDS")
    effect.setParameter("SelectedIslandIds", ",".join(map(str, island_ids)))
    effect.self().apply()

    print(f"✅ Kept island IDs {list(island_ids)} from IJK points in segment: {segmentID}")

def main():
    input_volume = import_dicom_series(DICOM_FOLDER, SERIES_DESCRIPTION)
    if not input_volume:
        print("❌ Volume not found.")
        return

    seed_fiducial = create_seed_fiducial(SEED_POINT_RAS)
    vesselness_volume = apply_vesselness_filter(input_volume, seed_fiducial, OUTPUT_VOLUME_NAME)

    try:
        segmentation_node = slicer.util.getNode(SEGMENTATION_NAME)
        print(f"✅ Found existing segmentation node: {SEGMENTATION_NAME}")
    except slicer.util.MRMLNodeNotFoundException:
        print(f"⚠️ Segmentation node '{SEGMENTATION_NAME}' not found. Creating...")
        segmentation_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", SEGMENTATION_NAME)
        segmentation_node.GetSegmentation().AddEmptySegment(SEGMENT_ID)
        segmentation_node.SetReferenceImageGeometryParameterFromVolumeNode(vesselness_volume)
        segmentation_node.CreateDefaultDisplayNodes()

    # Step 1: Fill segmentation from vesselness output
    fill_segmentation_from_volume(segmentation_node, SEGMENT_ID, vesselness_volume)

    # Step 2: Keep only the largest island
    keep_islands_by_ijk_coordinates(
        segmentationNode=slicer.util.getNode("VesselSegmentation"),
        segmentID="Segment_1",
        ijk_coords_list=SELECTED_VOXELS_TO_KEEP,
        volumeNode=slicer.util.getNode("FilteredVesselsPython")
    )
    
    # Step 3: Create surface and export
    segmentation_node.CreateClosedSurfaceRepresentation()
    
    export_segment_to_stl(segmentation_node, SEGMENT_ID, OUTPUT_FOLDER, EXPORT_FORMAT, COORDINATE_SYSTEM)

    # Setp 4: Export segmentation + image to .nii.gz files
    export_segmentation_and_volume_as_nifti(
        segmentation_node,
        vesselness_volume,
        os.path.join(OUTPUT_FOLDER, "circle_image.nii.gz"),
        os.path.join(OUTPUT_FOLDER, "circle_segmentation.nii.gz")
    )

main()


