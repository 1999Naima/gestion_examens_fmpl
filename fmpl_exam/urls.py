from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from examens import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path("examens/", include("examens.urls")),
    path('portal/', include('portal.urls', namespace='portal')),
    #path('admin/dashboard-stats/', include('examens.urls')),
# ou directement :
   path('admin/dashboard-stats/', views.dashboard_stats),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)