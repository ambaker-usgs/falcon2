from django.urls import include, path, re_path
from django.views.decorators.cache import cache_page

from falcon.views import views

urlpatterns = [
    path('', cache_page(60 * 5)(views.index), name='index'),
    path('refresh', views.index, name='index'),
    path('falconer', include('falconer.urls')),
    re_path(r'^(?P<network>[\w+]{2})/$', cache_page(60 * 6)(views.network_level), name='network_level'),
    re_path(r'^(?P<network>[\w+]{2})/(?P<station>\w+)/$', views.station_level),
    re_path(r'^(?P<network>[\w+]{2})/(?P<station>\w+)/(?P<channel>\w+)/$', views.channel_level, name='channel_level'),
    re_path(r'^api/(?P<network>[\w+]{2})/(?P<station>\w+)/(?P<channel>\w+)/$', views.api_channel_data, name='channel_data'),
]
