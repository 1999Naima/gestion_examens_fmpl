# portal/admin.py
from django.contrib import admin
from django.contrib.auth.models import User
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name = "Profil"


admin.site.unregister(User)

@admin.register(User)
class CustomUserAdmin(admin.ModelAdmin):
    inlines = [UserProfileInline]
    list_display  = ("username", "get_role", "get_surveillant", "is_active")
    list_filter   = ("profile__role",)
    search_fields = ("username",)

    def get_role(self, obj):
        return obj.profile.get_role_display() if hasattr(obj, "profile") else "-"
    get_role.short_description = "Rôle"

    def get_surveillant(self, obj):
        if hasattr(obj, "profile") and obj.profile.surveillant:
            return obj.profile.surveillant.nom
        return "-"
    get_surveillant.short_description = "Surveillant lié"


from portal.models import UserProfile, Presence

@admin.register(Presence)
class PresenceAdmin(admin.ModelAdmin):
    list_display  = ('etudiant', 'repartition', 'present', 'scanne_par', 'heure_scan')
    list_filter   = ('present', 'repartition__examen__date', 'repartition__amphi')
    search_fields = ('etudiant__nom', 'etudiant__prenom', 'etudiant__apogee')
    readonly_fields = ('heure_scan',)
    list_per_page = 50

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'etudiant', 'repartition__examen', 'repartition__amphi', 'scanne_par'
        )
