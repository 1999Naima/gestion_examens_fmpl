# examens/admin.py
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from etudiants.models import Etudiant
from examens.models import Examen, Repartition, Session
from .forms import RepartitionAdminForm

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('nom', 'type', 'date_debut', 'date_fin', 'is_active')
    list_filter = ('type', 'is_active')
    search_fields = ('nom',)
    list_editable = ('is_active',)

@admin.register(Examen)
class ExamenAdmin(admin.ModelAdmin):
    list_display = (
        "module",
        "session",
        "date",
        "display_niveau",
        "display_semester",  # Added semester field
        "annee",
    )
    list_filter = ('niveau', 'semester', 'annee', 'session', 'date')  # Added semester to filters
    search_fields = ('module',)
    
    def display_niveau(self, obj):
        return obj.get_niveau_display()
    display_niveau.short_description = "Niveau"
    
    def display_semester(self, obj):
        return obj.get_semester_display()
    display_semester.short_description = "Semestre"

@admin.register(Repartition)
class RepartitionAdmin(admin.ModelAdmin):
    form = RepartitionAdminForm
    filter_horizontal = ("etudiants",)
    change_form_template = "admin/examens/repartition/change_form.html"
    list_display = ('examen', 'amphi', 'get_students_count', 'get_surveillants_count', 'presence_button', 'proces_verbal_button')
    list_filter = ('examen__niveau', 'examen__semester', 'examen__annee', 'amphi')  # Added semester to filters
    search_fields = ('examen__module', 'amphi__nom')
    actions = ['generate_presence_list']
    
    # Proces Verbal button
    def proces_verbal_button(self, obj):
        """Add Proces Verbal button only"""
        return format_html(
            '<a class="button" href="/examens/proces-verbal/{}/" target="_blank" style="background-color: #dc3545; color: white;">📄 Procès Verbal</a>',
            obj.id
        )
    proces_verbal_button.short_description = "Procès Verbal"

    # Presence button
    def presence_button(self, obj):
        """Add a button in list display"""
        return format_html(
            '<a class="button" href="/examens/presence-pdf/{}/" target="_blank" style="background-color: #17a2b8; color: white;">📋 Liste de présence</a>',
            obj.id
        )
    presence_button.short_description = "Liste de présence"
    
    def generate_presence_list(self, request, queryset):
        """Admin action to generate presence list for selected repartitions"""
        if queryset.count() == 1:
            repartition = queryset.first()
            return HttpResponseRedirect(f'/examens/presence-pdf/{repartition.id}/')
        else:
            ids = ','.join(str(r.id) for r in queryset)
            return HttpResponseRedirect(f'/examens/presence-multiple-pdf/?ids={ids}')
    generate_presence_list.short_description = "Générer la liste de présence"
    
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.request = request
        return form
    
    def get_students_count(self, obj):
        return obj.etudiants.count()
    get_students_count.short_description = "Nombre d'étudiants"
    
    def get_surveillants_count(self, obj):
        return obj.surveillants.count()
    get_surveillants_count.short_description = "Nombre de surveillants"
    
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
    
    class Media:
        js = ('https://code.jquery.com/jquery-3.6.0.min.js',)

class ExamensAdminSite(admin.AdminSite):
    site_header = "FMPL Examens"
    site_title = "FMPL Examens Admin"
    index_title = "Examens Management"

admin_site = ExamensAdminSite(name="fmpl_admin")