from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from etudiants.models import Annee, Etudiant
# Register your models here.
admin.site.register(Annee)
@admin.register(Etudiant)
class EtudiantAdmin(ImportExportModelAdmin):
    list_display = ("nom", "prenom", "apogee", "cin", "annee")
    search_fields = ("nom", "prenom", "apogee")

