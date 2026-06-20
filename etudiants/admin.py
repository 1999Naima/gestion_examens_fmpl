from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from etudiants.models import Annee, Etudiant

@admin.register(Annee)
class AnneeAdmin(admin.ModelAdmin):
    list_display = ("id","filiere", "annee_universitaire")
    search_fields = ("filiere", "annee_universitaire")
    list_filter = ("filiere",)


@admin.register(Etudiant)
class EtudiantAdmin(ImportExportModelAdmin):
    list_display = ("nom", "prenom", "apogee", "niveau", "annee")
    search_fields = ("nom", "prenom", "apogee")
    list_filter = ("niveau", "annee")
    ordering = ("nom", "prenom")
    fieldsets = (
        (None, {
            'fields': ('nom', 'prenom', 'apogee', 'niveau', 'annee')
        }),
    )
    list_per_page = 25
    list_select_related = ('annee',)