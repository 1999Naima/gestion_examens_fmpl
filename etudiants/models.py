from django.db import models

# Create your models here.
class Annee(models.Model):
    filiere = models.CharField(max_length=100)
    annee_universitaire = models.CharField(max_length=9)
   

    def __str__(self):
        return f"{self.annee_universitaire}-{self.filiere}"
    
class Etudiant(models.Model):
    NIVEAU_CHOICES = [
        ('1', '1ère Année'),
        ('2', '2ème Année'),
        ('3', '3ème Année'),
        ('4', '4ème Année'),
        ('5', '5ème Année'),
    ]
    
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    apogee = models.CharField(max_length=20)
    niveau = models.CharField(max_length=2, choices=NIVEAU_CHOICES)  # Stocke "1", "2", etc.
    annee = models.ForeignKey(Annee, on_delete=models.CASCADE)
    
    def __str__(self):
        return f"{self.nom} {self.prenom}"
    
   