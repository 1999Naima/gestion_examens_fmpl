from django.db import models
from django.forms import ValidationError

from etudiants.models import Annee, Etudiant
from salles.models import Amphi
from surveillants.models import Surveillant


class Session(models.Model):
    SESSION_TYPES = [
        ('normal', 'Normal'),
        ('rattrapage', 'Rattrapage'),
    ]
    
    nom = models.CharField(max_length=100)  # "Mai 2026", "Septembre 2026"
    type = models.CharField(max_length=20, choices=SESSION_TYPES, default='normal')
    date_debut = models.DateField()
    date_fin = models.DateField()
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-date_debut']
    
    def __str__(self):
        return f"{self.nom} ({self.get_type_display()})"
    
# Create your models here.
class Examen(models.Model):
    module = models.CharField(max_length=150)
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='examens')
    date = models.DateField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    niveau = models.CharField(max_length=2,choices=Etudiant.NIVEAU_CHOICES)
    annee = models.ForeignKey(Annee,on_delete=models.CASCADE)
    def __str__(self):
     return f"{self.module} - {self.session} - {self.get_niveau_display()}"
    

    def clean(self):
        from django.core.exceptions import ValidationError
        from datetime import time

        # ✅ 1. End time must be after start time
        if self.heure_fin <= self.heure_debut:
            raise ValidationError({
                'heure_fin': "L'heure de fin doit être après l'heure de début."
            })

        # ✅ 2. Check overlapping exams for the SAME DATE, SAME YEAR, AND SAME LEVEL
        conflits = Examen.objects.filter(
            date=self.date,
            annee=self.annee,
            niveau=self.niveau  # ← FIXED: Added niveau to filter
        ).exclude(pk=self.pk)

        for exam in conflits:
            overlap = (
                self.heure_debut < exam.heure_fin and
                self.heure_fin > exam.heure_debut
            )

            if overlap:
                raise ValidationError(
                    f"Conflit avec l'examen '{exam.module}' "
                    f"({exam.heure_debut} - {exam.heure_fin}) "
                    f"pour le même niveau ({self.get_niveau_display()}) "
                    f"et la même année universitaire."
                )

class Repartition(models.Model):
    examen = models.ForeignKey(Examen,on_delete=models.CASCADE)
    surveillants = models.ManyToManyField(Surveillant)
    amphi = models.ForeignKey(Amphi,on_delete=models.CASCADE)
    etudiants = models.ManyToManyField(Etudiant, blank=True)  
    def __str__(self):
        return f"{self.examen} - {self.amphi}"


