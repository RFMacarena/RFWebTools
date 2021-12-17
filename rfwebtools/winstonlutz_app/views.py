from django.shortcuts import render
from django.http import HttpResponse, Http404
from .wl_form import WinstonLutzTest_Form
from datetime import datetime
from BallBearing.Ball_Bearing_Winston_Lutz import Read_arguments,Read_arguments_from_txt, Get_Laser, Get_centro_radiacion
from BallBearing.Ball_Bearing_Winston_Lutz import Evaluacion, Genera_Informe
from BallBearing.orthanc_queries import get_bb_images_from_orthanc
from django.conf import settings
import os

context = {}

# Create your views here.
def winstonlutztest(request):
    if request.method == "POST":

        form_winstonlutztest = WinstonLutzTest_Form(request.POST)
        if form_winstonlutztest.is_valid():
            linac = form_winstonlutztest["linac_choice"].value()
            date1 = datetime.strptime(form_winstonlutztest['date1'].value(), "%Y-%m-%d")
            if linac:
                run_winstonlutz(date1,linac)
                message = f'Fecha: {date1}, ' \
                          f'ALE: {linac}, '
                message_report = "Descargar informe de resultados"
                context = {'form_winstonlutztest': form_winstonlutztest,
                           'mensaje': message,
                           'mensaje_informe': message_report}

            else:
                message = "Debes rellenar algun campo."
                context = {'form_winstonlutztest': form_winstonlutztest,
                            'mensaje': message}

        else:
            message = "Input invalido"
            context = {'form_winstonlutztest': form_winstonlutztest, 'mensaje': message}
        return render(request, 'winstonlutz.html', context)
    else:
        form_winstonlutztest = WinstonLutzTest_Form()
        context = {'form_winstonlutztest': form_winstonlutztest}
        # context = {}
        return render(request, 'winstonlutz.html', context)

def download_file(request,fname):
    global df_resultados

    file_path = os.path.join(settings.MEDIA_ROOT[0], fname)
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type="'application/pdf'")
            response['Content-Disposition'] = 'inline; filename=' + os.path.basename(file_path)
            return response
    raise Http404

def run_winstonlutz(date1,linac):

    path_media = settings.MEDIA_ROOT[0]
    fname = "Nombres_ficheros_winston_Lutz.txt"
    argument_file = file_path = os.path.join(settings.MEDIA_ROOT[0], fname)
    sigma = 2
    low = 5
    high = 30

    im_dic = get_bb_images_from_orthanc(date1, linac)

    # Lee nombres de los ficheros del fichero de argumentos self.argument_file y genera el array de "imagenes"
    # Tambien las analiza y obtiene centro de radiacion y centro de los laseres.
    ra = Read_arguments(im_dic, sigma, low, high)
    #ra = Read_arguments_from_txt(argument_file, sigma, low, high)

    # Calcula la posicion 3D del laser para gantry, colimador, mesa y todo combinado
    print("Evaluando posicion laseres ...")
    gl = Get_Laser(ra.imagenes)

    # Calcula la posicion 3D del centro de radiacion para gantry, colimador, mesa y todo combinado
    print("Evaluando posicion centro radiacion ...")
    gc = Get_centro_radiacion(ra.imagenes)

    # Evaluacion de resultados
    print("Evaluando de resultados ...")
    ge = Evaluacion(ra.imagenes, gl, gc)

    # Generacion de Informe
    Genera_Informe(path_media, im_dic['G0'].pixel_array, ra.imagenes, gl, gc)

