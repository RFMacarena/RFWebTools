from pyorthanc import Orthanc, Patient, Series, Study, Instance
from pyorthanc.util import _build_patient as build_patient
from dicompylercore import dicomparser, dvh, dvhcalc
import pydicom as dicom
from datetime import datetime
import io
import numpy as np
from .serverdata import ORTHANC_URL,USER_ORTHANC,PASSWORD_ORTHANC


def get_bb_images_from_orthanc(date1,linac):
    orthanc = Orthanc(ORTHANC_URL)  # 'http://10.233.42.60:8042')     # ('http://localhost:8042')
    orthanc.setup_credentials(USER_ORTHANC, PASSWORD_ORTHANC)
    patID = "AN000002"
    fecha = str(date1.year) + str(date1.month) + str(date1.day)
    campos = ['G0', 'G90', 'G180', 'G270', 'C90', 'C180', 'C270', 'M90', 'M270']
    im_dic = {}
    stationname_dic = {"ALE1": "SEVMVersa1_iView",
                       "ALE2": "SEVMVersa2"}
    # StudyID: Winston_Lutz_FPV, SeriesDescription: NombreCampo, "StationName": "SEVMVersa2"
    instance_identifiers = orthanc.c_find({"Level": "Instance",
                                       "Query": {"Modality": "RTIMAGE",
                                                 "StudyID": "Winston_Lutz_FPV",
                                                 "AcquisitionDate":fecha,
                                                 "StationName": stationname_dic[linac],
                                                 "PatientID": patID}})

    im_instances = [Instance(x, orthanc) for x in instance_identifiers]

    for inst in im_instances:
        print(f'Nombre campo: {inst.get_simplified_tags()["SeriesDescription"]}')

    for campo in campos:
        for inst in im_instances:
            if campo in inst.get_simplified_tags()["SeriesDescription"]:
                im_dcm = dicom.dcmread(io.BytesIO(orthanc.get_instance_file(inst.get_identifier())))
                im_dic[campo] = im_dcm

    return im_dic