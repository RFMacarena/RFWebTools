from django import forms
import datetime

class DateInput(forms.DateInput):
    input_type = "date"

class WinstonLutzTest_Form(forms.Form):
    linac_list = ['ALE1', 'ALE2', 'ALE3']
    LINAC_CHOICES = list(zip(linac_list, linac_list))
    date1 = forms.DateTimeField(label="Fecha", widget=DateInput)
    linac_choice = forms.CharField(label='ALE', widget=forms.Select(choices=LINAC_CHOICES))
