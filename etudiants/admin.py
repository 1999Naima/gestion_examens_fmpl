from django.contrib import admin
from import_export.admin import ImportExportModelAdmin

from etudiants.models import Annee, Etudiant
# Register your models here.

admin.site.register(Annee)
@admin.register(Etudiant)
class EtudiantAdmin(ImportExportModelAdmin):
    list_display = ("nom", "prenom", "apogee","niveau", "annee")
    search_fields = ("nom", "prenom", "apogee")

    # Add filters here
    list_filter = ("niveau", "annee")  # This adds filters in the right sidebar
    
    # Optional: Add ordering
    ordering = ("nom", "prenom")
    
    # Optional: Add fields to display in the detail form
    fieldsets = (
        (None, {
            'fields': ('nom', 'prenom', 'apogee', 'niveau', 'annee')
        }),
    )
    
    # Optional: Make the admin list page more useful
    list_per_page = 25  # Show 25 items per page
    list_select_related = ('annee',)  # Optimize foreign key queries

