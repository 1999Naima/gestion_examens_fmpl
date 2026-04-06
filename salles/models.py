from django.db import models

# Create your models here.
class Amphi(models.Model):
    nom = models.CharField(max_length=50)
    capacite = models.IntegerField()

    def __str__(self):
        return self.nom