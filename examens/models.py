# examens/models.py
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
    

class Examen(models.Model):
    # Semester choices from 1 to 12
    SEMESTER_CHOICES = [
        ('1', 'Semestre 1'),
        ('2', 'Semestre 2'),
        ('3', 'Semestre 3'),
        ('4', 'Semestre 4'),
        ('5', 'Semestre 5'),
        ('6', 'Semestre 6'),
        ('7', 'Semestre 7'),
        ('8', 'Semestre 8'),
        ('9', 'Semestre 9'),
        ('10', 'Semestre 10'),
        ('11', 'Semestre 11'),
        ('12', 'Semestre 12'),
    ]
    
    module = models.CharField(max_length=150)
    semester = models.CharField(max_length=2, choices=SEMESTER_CHOICES, default='1', verbose_name="Semestre")
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='examens')
    date = models.DateField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    niveau = models.CharField(max_length=2, choices=Etudiant.NIVEAU_CHOICES)
    annee = models.ForeignKey(Annee, on_delete=models.CASCADE)
    
    
    def __str__(self):
        return f"{self.module} - {self.session} - {self.get_niveau_display()} - {self.get_semester_display()}"
    
    def get_semester_display(self):
        """Return 'Semestre 1' instead of '1'"""
        return dict(self.SEMESTER_CHOICES).get(self.semester, self.semester)

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
            niveau=self.niveau
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
    examen = models.ForeignKey(Examen, on_delete=models.CASCADE)
    surveillants = models.ManyToManyField(Surveillant)
    amphi = models.ForeignKey(Amphi, on_delete=models.CASCADE)
    etudiants = models.ManyToManyField(Etudiant, blank=True)
    
    def __str__(self):
        return f"{self.examen} - {self.amphi}"
    


from salles.models import siege

class Repartitionsiege(models.Model):
    repartition = models.ForeignKey(Repartition, on_delete=models.CASCADE, related_name='siege_assignments')
    etudiant    = models.ForeignKey('etudiants.Etudiant', on_delete=models.CASCADE)
    siege        = models.ForeignKey(siege, on_delete=models.CASCADE)
    numero      = models.IntegerField()  # numéro d'ordre dans la salle

    class Meta:
        unique_together = [('repartition', 'siege'), ('repartition', 'etudiant')]

    def __str__(self):
        return f"N°{self.numero} — {self.etudiant} → {self.siege}"