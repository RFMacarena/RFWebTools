from django.shortcuts import render
from django.shortcuts import HttpResponse
from .wl_form import WinstonLutzTest_Form
from datetime import datetime
#from ..BallBearing.Ball_Bearing_Winston_Lutz import Recta


context = {}

# Create your views here.
def winstonlutztest(request):
    if request.method == "POST":

        form_winstonlutztest = WinstonLutzTest_Form(request.POST)
        if form_winstonlutztest.is_valid():
            linac = form_winstonlutztest["linac_choice"].value()
            date1 = datetime.strptime(form_winstonlutztest['date1'].value(), "%Y-%m-%d")
            if linac:
                message = f'Fecha: {date1}, ' \
                          f'ALE: {linac}, '

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

