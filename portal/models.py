# portal/models.py
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ("surveillant", "Surveillant"),
        ("admin",       "Administrateur"),
    ]
    user        = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role        = models.CharField(max_length=20, choices=ROLE_CHOICES, default="surveillant")
    surveillant = models.OneToOneField(
        "surveillants.Surveillant", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="user_profile"
    )

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

    class Meta:
        verbose_name        = "Profil utilisateur"
        verbose_name_plural = "Profils utilisateurs"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()


class Presence(models.Model):
    """Records whether a student was present in an exam."""
    repartition = models.ForeignKey(
        "examens.Repartition", on_delete=models.CASCADE, related_name="presences"
    )
    etudiant = models.ForeignKey(
        "etudiants.Etudiant", on_delete=models.CASCADE, related_name="presences"
    )
    present     = models.BooleanField(default=True)
    scanne_par  = models.ForeignKey(
        "surveillants.Surveillant", null=True, blank=True,
        on_delete=models.SET_NULL, related_name="presences_marquees"
    )
    heure_scan  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together     = ("repartition", "etudiant")
        verbose_name        = "Présence"
        verbose_name_plural = "Présences"

    def __str__(self):
        status = "Présent" if self.present else "Absent"
        return f"{self.etudiant} — {self.repartition.examen.module} — {status}"