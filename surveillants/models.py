from django.db import models

# Create your models here.
class Surveillant(models.Model):
    nom = models.CharField(max_length=100)
    specialite = models.CharField(max_length=100)
    email      = models.EmailField(max_length=150, blank=True, null=True)
    telephone  = models.CharField(max_length=20, blank=True, null=True)
    def __str__(self):
        return self.nom