from pyorthanc import Orthanc
from pyorthanc.instance import Instance
from serverdata import *
import io
import pydicom as dicom
from datetime import datetime

def test():
    fecha = "20211011"
    f1 = datetime.now()
    fecha_str = str(f1.year)+str(f1.month)+str(f1.day)
    get_bb_images_from_orthanc(fecha_str)

def get_bb_images_from_orthanc(fecha):
    orthanc = Orthanc(ORTHANC_URL)  # 'http://10.233.42.60:8042')     # ('http://localhost:8042')
    orthanc.setup_credentials(USER_ORTHANC, PASSWORD_ORTHANC)
    patID = "AN000002"
    fecha = "20211011"
    campos = ['G0', 'G90', 'G180', 'G270', 'C90', 'C180', 'C270', 'M90', 'M270']
    im_dic = {}
    # StudyID: Winston_Lutz_FPV, SeriesDescription: NombreCampo, "StationName": "SEVMVersa2"
    instance_identifiers = orthanc.c_find({"Level": "Instance",
                                       "Query": {"Modality": "RTIMAGE",
                                                 "StudyID": "Winston_Lutz_FPV",
                                                 "AcquisitionDate":fecha,
                                                 "PatientID": patID}})

    print(instance_identifiers)

    im_instances = [Instance(x, orthanc) for x in instance_identifiers]

    for inst in im_instances:
        print(f'Nombre campo: {inst.get_simplified_tags()["SeriesDescription"]}')

    for campo in campos:
        for inst in im_instances:
            if campo in inst.get_simplified_tags()["SeriesDescription"]:
                im_dcm = dicom.dcmread(io.BytesIO(orthanc.get_instance_file(inst.get_identifier())))
                im_dic[campo] = im_dcm
    print(im_dic)

test()