from django.db import models

from etudiants.models import Annee, Etudiant
from salles.models import Amphi
from surveillants.models import Surveillant

# Create your models here.
class Examen(models.Model):
    module = models.CharField(max_length=150)
    session = models.CharField(max_length=50)
    date = models.DateField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    annee = models.ForeignKey(Annee,on_delete=models.CASCADE)

class Repartition(models.Model):
    examen = models.ForeignKey(Examen,on_delete=models.CASCADE)
    surveillant = models.ForeignKey(Surveillant,on_delete=models.CASCADE)
    amphi = models.ForeignKey(Amphi,on_delete=models.CASCADE)
    role = models.CharField(max_length=50)


class AffectationEtudiant(models.Model):
    etudiant = models.ForeignKey(Etudiant,on_delete=models.CASCADE)
    examen = models.ForeignKey(Examen,on_delete=models.CASCADE)
    amphi = models.ForeignKey(Amphi,on_delete=models.CASCADE)
    present = models.BooleanField(default=False)