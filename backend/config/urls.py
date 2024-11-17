from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def root_view(request):
    return JsonResponse({"message": "API root"})

urlpatterns = [
    path('', root_view, name='api-root'),
    path('admin/', admin.site.urls),
    path('api/', include('core.urls')),
] 