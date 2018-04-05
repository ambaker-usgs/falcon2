from django.urls import path, re_path

from falcon.views import views

urlpatterns = [
    path('', views.index, name='index'),
    path('falconer', views.falconer, name='falconer'),
    re_path(r'^(?P<network>[\w+]{2})/$', views.network_level),
    re_path(r'^(?P<network>[\w+]{2})/(?P<station>\w+)/$', views.station_level),
    re_path(r'^(?P<network>[\w+]{2})/(?P<station>\w+)/(?P<channel>\w+)/$', views.channel_level),
]