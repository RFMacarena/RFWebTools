from pyorthanc import Orthanc, Patient, Series, Study, Instance
from pyorthanc.util import _build_patient as build_patient
from dicompylercore import dicomparser, dvh, dvhcalc
import pydicom as dicom
from datetime import datetime
import io
import numpy as np
from .serverdata import ORTHANC_URL,USER_ORTHANC,PASSWORD_ORTHANC


def find_patient(orthanc_conect=None, patient_name="", patient_id=""):
    patients_identifiers = orthanc_conect.c_find(
        {"Level": "Patient", "Query": {"PatientID": patient_id, "PatientName": patient_name}})

    return patients_identifiers

def get_orthanc_images(linac,date1):

    return

def buscar_instancias_dicomRT(orthanc_conect, patient_identifier):
    study_dat = {}

    # patient = build_patient(instance_identifier, orthanc_conect, None, None, None)
    # return patient
    patient_info = orthanc_conect.get_patient_information(patient_identifier)
    studies_info = orthanc_conect.get_patient_studies_information(patient_identifier)
    for study in studies_info:

        series = orthanc_conect.get_study_series_information(study['ID'])

        instance_id = {}
        for serie in series:

            if serie['MainDicomTags']['Modality'] == 'RTPLAN':
                plan_instance = serie['Instances'][0]
                instance_id['RTPLAN'] = plan_instance
                # plan_dcm = dicom.dcmread(
                #     io.BytesIO(orthanc_conect.get_instance_file(plan_instance)))
            elif serie['MainDicomTags']['Modality'] == 'RTSTRUCT':
                struct_instance = serie['Instances'][0]
                instance_id['RTSTRUCT'] = struct_instance
                # struct_dcm = dicom.dcmread(
                #     io.BytesIO(orthanc_conect.get_instance_file(struct_instance)))
            elif serie['MainDicomTags']['Modality'] == 'RTDOSE':
                dose_instance = serie['Instances'][0]
                instance_id['RTDOSE'] = dose_instance
                # dose_dcm = dicom.dcmread(
                #     io.BytesIO(orthanc_conect.get_instance_file(dose_instance)))

        study_dat['Instances'] = instance_id
    return study_dat