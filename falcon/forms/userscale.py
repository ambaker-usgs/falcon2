from django import forms


class UserScalingForm(forms.Form):

    ymin = forms.DateTimeField(widget=forms.TextInput(attrs={'class': "ui-widget ui-corner-all"}),
                               label='Y Minimum'
                               )

    ymax = forms.DateTimeField(widget=forms.TextInput(attrs={'class': "ui-widget ui-corner-all"}),
                               label='Y Maximum'
                               )

    startdate = forms.DateTimeField(widget=forms.TextInput(attrs={'class': "ui-widget ui-corner-all"}),
                                     label='Start Date'
                                     )

    enddate = forms.DateTimeField(widget=forms.TextInput(attrs={'class': "ui-widget ui-corner-all"}),
                                   label='End Date'
                                   )
