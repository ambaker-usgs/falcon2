from django.urls import path, re_path
from django.views.decorators.cache import cache_page

from falcon.views import views

urlpatterns = [
    path('', cache_page(60 * 1)(views.index), name='index'),
    path('refresh', views.index, name='index'),
    path('falconer', views.falconer, name='falconer'),
    re_path(r'^(?P<network>[\w+]{2})/$', views.network_level),
    re_path(r'^(?P<network>[\w+]{2})/(?P<station>\w+)/$', views.station_level),
    re_path(r'^(?P<network>[\w+]{2})/(?P<station>\w+)/(?P<channel>\w+)/$', views.channel_level),
]
