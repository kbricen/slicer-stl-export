
# === slicer_stl_export.py ===
import slicerutil
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
    COORDINATE_SYSTEM
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

def main_old():
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

    # Fill it using threshold
    fill_segmentation_from_volume(segmentation_node, SEGMENT_ID, vesselness_volume)

    segmentation_node.CreateClosedSurfaceRepresentation()
    export_segment_to_stl(segmentation_node, SEGMENT_ID, OUTPUT_FOLDER, EXPORT_FORMAT, COORDINATE_SYSTEM)

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

    # ✅ Step 2: Keep only the largest island
    keep_largest_island_in_segment(segmentation_node, SEGMENT_ID, vesselness_volume)

    # Step 3: Create surface and export
    segmentation_node.CreateClosedSurfaceRepresentation()
    export_segment_to_stl(segmentation_node, SEGMENT_ID, OUTPUT_FOLDER, EXPORT_FORMAT, COORDINATE_SYSTEM)

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
    keep_largest_island_in_segment(segmentation_node, SEGMENT_ID, vesselness_volume)

    # Step 3: Create surface and export
    segmentation_node.CreateClosedSurfaceRepresentation()
    
    export_segment_to_stl(segmentation_node, SEGMENT_ID, OUTPUT_FOLDER, EXPORT_FORMAT, COORDINATE_SYSTEM)

    # Export segmentation + image to .nii.gz files
    export_segmentation_and_volume_as_nifti(
        segmentation_node,
        vesselness_volume,
        os.path.join(OUTPUT_FOLDER, "circle_image.nii.gz"),
        os.path.join(OUTPUT_FOLDER, "circle_segmentation.nii.gz")
    )
    
main()


