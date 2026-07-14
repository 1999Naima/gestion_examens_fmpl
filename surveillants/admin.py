# surveillants/admin.py
from django.contrib import admin
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Surveillant


@admin.register(Surveillant)
class SurveillantAdmin(admin.ModelAdmin):
    list_display  = ("nom", "specialite", "has_account")
    search_fields = ("nom",)
    actions       = ["create_user_account"]

    def has_account(self, obj):
        return hasattr(obj, "user_profile")
    has_account.boolean = True
    has_account.short_description = "Compte créé"

    @admin.action(description="Créer un compte utilisateur pour le(s) surveillant(s) sélectionné(s)")
    def create_user_account(self, request, queryset):
        from portal.models import UserProfile
        created, skipped = 0, 0

        for surveillant in queryset:
            if hasattr(surveillant, "user_profile"):
                skipped += 1
                continue

            base_username = surveillant.nom.upper()
            username = base_username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            user = User.objects.create_user(username=username, password="fmpl2026")

            # Use get_or_create because the signal may have already created a blank profile
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = "surveillant"
            profile.surveillant = surveillant
            profile.save()

            created += 1

        if created:
            self.message_user(request,
                f"{created} compte(s) créé(s). Mot de passe par défaut : fmpl2026",
                messages.SUCCESS)
        if skipped:
            self.message_user(request,
                f" {skipped} surveillant(s) avaient déjà un compte.",
                messages.WARNING)
    
   