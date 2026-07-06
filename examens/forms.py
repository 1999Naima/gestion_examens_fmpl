# examens/forms.py
from django import forms
from django.core.exceptions import ValidationError
from etudiants.models import Etudiant
from .models import Examen, Repartition

class RepartitionAdminForm(forms.ModelForm):
    
    class Meta:
        model = Repartition
        fields = "__all__"
    
    
    def clean(self):
        cleaned_data = super().clean()
        
        examen = cleaned_data.get("examen")
        amphi = cleaned_data.get("amphi")
        surveillants = cleaned_data.get("surveillants")
        etudiants = cleaned_data.get("etudiants")
        
        if not examen:
            return cleaned_data
        
        # Additional validation: ensure all students belong to correct niveau and annee
        if etudiants:
            invalid_students = etudiants.exclude(
                niveau=examen.niveau,
                annee=examen.annee
            )
            if invalid_students.exists():
                invalid_names = ", ".join([str(s) for s in invalid_students[:5]])
                raise ValidationError(
                    f"Les étudiants suivants n'appartiennent pas au niveau {examen.get_niveau_display()} "
                    f"et à l'année {examen.annee}: {invalid_names}"
                )
        
        # -----------------------------
        #  1. Surveillant conflict (check time overlap)
        # -----------------------------
        if surveillants:
            for surveillant in surveillants:
                # Get all repartitions where this surveillant is assigned on the same date
                conflicting_repartitions = Repartition.objects.filter(
                    surveillants=surveillant,
                    examen__date=examen.date
                ).exclude(pk=self.instance.pk)
                
                for rep in conflicting_repartitions:
                    other_exam = rep.examen
                    # Check if times overlap
                    time_overlap = (
                        examen.heure_debut < other_exam.heure_fin and
                        examen.heure_fin > other_exam.heure_debut
                    )
                    
                    if time_overlap:
                        raise ValidationError(
                            f"Surveillant '{surveillant.nom}' est déjà assigné à l'examen '{other_exam.module}' "
                            f"le même jour de {other_exam.heure_debut} à {other_exam.heure_fin}. "
                            f"Conflit d'horaire avec l'examen actuel ({examen.heure_debut} - {examen.heure_fin})."
                        )
        
        # -----------------------------
        # 2. Amphi conflict
        # -----------------------------
        if amphi:
            same_date_exams = Examen.objects.filter(date=examen.date).exclude(pk=examen.pk)
            
            for other_exam in same_date_exams:
                time_overlap = (
                    examen.heure_debut < other_exam.heure_fin and
                    examen.heure_fin > other_exam.heure_debut
                )
                
                if time_overlap:
                    amphi_conflict = Repartition.objects.filter(
                        examen=other_exam,
                        amphi=amphi
                    ).exists()
                    
                    if amphi_conflict:
                        raise ValidationError(
                            f"Amphi '{amphi}' est déjà utilisé pour '{other_exam.module}' "
                            f"({other_exam.heure_debut} - {other_exam.heure_fin})"
                        )
        
        # -----------------------------
        # 3. Prevent duplicate student assignment
        # -----------------------------
        if etudiants:
            for etudiant in etudiants:
                already_assigned = Repartition.objects.filter(
                    etudiants=etudiant,
                    examen=examen
                ).exclude(pk=self.instance.pk).exists()
                
                if already_assigned:
                    raise ValidationError(
                        f"L'étudiant '{etudiant}' est déjà assigné à cet examen"
                    )
        
        return cleaned_data