from django.db import models

# Create your models here.
class Annee(models.Model):
    nom = models.CharField(max_length=100)
    niveau = models.CharField(max_length=50)
    annee_universitaire = models.CharField(max_length=9)

    def __str__(self):
        return f"{self.nom} {self.niveau}"
    
class Etudiant(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    apogee = models.CharField(max_length=20)
    cin = models.CharField(max_length=20)
    annee = models.ForeignKey(Annee,on_delete=models.CASCADE)