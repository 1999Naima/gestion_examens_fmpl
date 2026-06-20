from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from examens import views

urlpatterns = [
    # ← dashboard-stats AVANT admin/
    path('admin/dashboard-stats/', views.dashboard_stats, name='dashboard_stats'),
    path('admin/', admin.site.urls),
    path("examens/", include("examens.urls")),
    path('portal/', include('portal.urls', namespace='portal')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)