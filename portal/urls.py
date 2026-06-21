# portal/urls.py
from django.urls import path
from . import views

app_name = "portal"

urlpatterns = [
    # Surveillant
    path("surveillant/login/",    views.surveillant_login,     name="surveillant_login"),
    path("surveillant/logout/",   views.surveillant_logout,    name="surveillant_logout"),
    path("surveillant/",          views.surveillant_dashboard, name="surveillant_dashboard"),
    path("surveillant/presence/", views.mark_presence,         name="mark_presence"),
    path("surveillant/scan-siege/", views.scan_siege, name="scan_siege"),
    # Étudiant
    path("etudiant/login/",       views.etudiant_login,        name="etudiant_login"),
    path("etudiant/logout/",      views.etudiant_logout,       name="etudiant_logout"),
    path("etudiant/",             views.etudiant_dashboard,    name="etudiant_dashboard"),

]