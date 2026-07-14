# examens/admin.py
from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html
from django.http import HttpResponseRedirect
from etudiants.models import Annee, Etudiant
from examens.models import Examen, Repartition, Session
from examens.views import convocations_view
from .forms import RepartitionAdminForm

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('nom', 'type', 'date_debut', 'date_fin', 'is_active')
    list_filter = ('type', 'is_active')
    search_fields = ('nom',)
    list_editable = ('is_active',)

@admin.register(Examen)
class ExamenAdmin(admin.ModelAdmin):
    list_display = ("module", "session", "date", "display_niveau", "display_semester", "annee")
    list_filter = ('niveau', 'semester', 'annee', 'session', 'date')
    search_fields = ('module',)

    def display_niveau(self, obj):
        return obj.get_niveau_display()
    display_niveau.short_description = "Niveau"

    def display_semester(self, obj):
        return obj.get_semester_display()
    display_semester.short_description = "Semestre"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "session":
            kwargs["queryset"] = Session.objects.filter(is_active=True)
        if db_field.name == "annee":
            kwargs["queryset"] = Annee.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        active_session = Session.objects.filter(is_active=True).first()
        if active_session:
            initial['session'] = active_session.pk

        active_annee = Annee.objects.filter(is_active=True).first()
        if active_annee:
            initial['annee'] = active_annee.pk

        return initial

@admin.register(Repartition)
class RepartitionAdmin(admin.ModelAdmin):
    form = RepartitionAdminForm
    filter_horizontal = ("etudiants",)
    change_form_template = "admin/examens/repartition/change_form.html"
    #list_display = ('examen', 'amphi', 'get_students_count', 'get_surveillants_count', 'presence_button', 'proces_verbal_button')
    #list_filter = ('examen__niveau', 'examen__semester', 'examen__annee', 'amphi')
    list_display = ('examen', 'amphi', 'get_students_count', 'get_surveillants_count', 'sieges_status', 'presence_button', 'proces_verbal_button')
    list_filter = ('examen__niveau', 'examen__semester', 'examen__annee', 'amphi')
    search_fields = ('examen__module', 'amphi__nom')
    actions = ['generate_presence_list', 'assigner_sieges']  # ← ajouté ici

    def proces_verbal_button(self, obj):
        return format_html(
            '<a class="button" href="/examens/proces-verbal/{}/" target="_blank" style="background-color: #dc3545; color: white;">📄 Procès Verbal</a>',
            obj.id
        )
    proces_verbal_button.short_description = "Procès Verbal"

    def presence_button(self, obj):
        return format_html(
            '<a class="button" href="/examens/presence-pdf/{}/" target="_blank" style="background-color: #17a2b8; color: white;">📋 Liste de présence</a>',
            obj.id
        )
    presence_button.short_description = "Liste de présence"

    def generate_presence_list(self, request, queryset):
        if queryset.count() == 1:
            repartition = queryset.first()
            return HttpResponseRedirect(f'/examens/presence-pdf/{repartition.id}/')
        else:
            ids = ','.join(str(r.id) for r in queryset)
            return HttpResponseRedirect(f'/examens/presence-multiple-pdf/?ids={ids}')
    generate_presence_list.short_description = "Générer la liste de présence"

    def assigner_sieges(self, request, queryset):  # ← méthode de la classe
        from salles.models import siege
        from examens.models import Repartitionsiege

        for rep in queryset:
            sieges     = list(rep.amphi.sieges.order_by('siege_number'))
            etudiants = list(rep.etudiants.order_by('nom', 'prenom'))

            if len(sieges) < len(etudiants):
                self.message_user(request,
                    f" {rep.amphi.nom} : {len(sieges)} sièges mais {len(etudiants)} étudiants.",
                    messages.WARNING)
                continue

            Repartitionsiege.objects.filter(repartition=rep).delete()

            for i, (etudiant, siege) in enumerate(zip(etudiants, sieges), start=1):
                Repartitionsiege.objects.create(
                    repartition=rep,
                    etudiant=etudiant,
                    siege=siege,
                    numero=i,
                )

            self.message_user(request,
                f" {len(etudiants)} sièges assignés pour {rep.amphi.nom}.",
                messages.SUCCESS)
    assigner_sieges.short_description = "Assigner les sièges automatiquement"

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

    def sieges_status(self, obj):
        from examens.models import Repartitionsiege
        assigned = Repartitionsiege.objects.filter(repartition=obj).count()
        total    = obj.etudiants.count()
        if assigned == 0:
            return format_html(
                '<span style="color:#c0392b;font-weight:600;font-size:13px">'
                '✗ Non assigné</span>'
            )
        elif assigned < total:
            return format_html(
                '<span style="color:#e67e22;font-weight:600;font-size:13px">'
                '⚠ Partiel ({}/{})</span>',
                assigned, total
            )
        else:
            return format_html(
                '<span style="color:#27ae60;font-weight:600;font-size:13px">'
                '✓ Assigné ({})</span>',
                assigned
            )
    sieges_status.short_description = "Sièges"
  
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

    class Media:
        js = ('https://code.jquery.com/jquery-3.6.0.min.js',)


from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView
from django.urls import path
class CalendrierAdminView(TemplateView):
    template_name = "admin/examens/calendrier.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(admin.site.each_context(self.request))
        
        from examens.models import Examen, Session
        from etudiants.models import Annee
        from datetime import date
        
        sessions = Session.objects.filter(is_active=True).order_by('-date_debut')
        session_id = self.request.GET.get('session')
        selected_session = None

        # ── Filtre par filière ──
        filiere = self.request.GET.get('filiere')
        filieres = (Annee.objects
                    .values_list('filiere', flat=True)
                    .distinct()
                    .order_by('filiere'))

        examens_qs = Examen.objects.select_related('annee', 'session')

        if session_id:
            selected_session = Session.objects.get(pk=session_id)
            examens_qs = examens_qs.filter(session_id=session_id)
        else:
            examens_qs = examens_qs.filter(session__is_active=True)

        if filiere:
            examens_qs = examens_qs.filter(annee__filiere=filiere)

        examens = examens_qs.order_by('date', 'heure_debut')

        # Organise par date
        from collections import defaultdict
        examens_by_date = defaultdict(list)
        for examen in examens:
            examens_by_date[examen.date].append(examen)

        context['sessions']          = sessions
        context['selected_session']  = selected_session
        context['examens_by_date']   = dict(sorted(examens_by_date.items()))
        context['niveaux']           = ['1','2','3','4','5']
        context['filieres']          = filieres
        context['selected_filiere']  = filiere
        context['title']             = 'Calendrier des Examens'
        return context
       
# À la fin de examens/admin.py
from django.urls import path
from django.contrib import admin

original_get_urls = admin.site.get_urls

def custom_get_urls():
    urls = original_get_urls()

    custom_urls = [
        path(
            "examens/convocations/",
            admin.site.admin_view(convocations_view),
            name="examens_convocations",
        ),
        path(
            "examens/calendrier/",
            admin.site.admin_view(CalendrierAdminView.as_view()),
            name="examens_calendrier",
        ),
    ]

    return custom_urls + urls

admin.site.get_urls = custom_get_urls