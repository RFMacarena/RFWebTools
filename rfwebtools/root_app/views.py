from django.shortcuts import render
from winstonlutz_app.wl_form import WinstonLutzTest_Form

# Create your views here.

def home(request):
    return render(request,'home.html',{})

def winstonlutz(request):
    form_winstonlutztest = WinstonLutzTest_Form()
    context = {'form_winstonlutztest': form_winstonlutztest}
    # context = {}
    return render(request, 'winstonlutz.html', context)