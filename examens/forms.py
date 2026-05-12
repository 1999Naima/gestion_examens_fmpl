# examens/forms.py
from django import forms
from django.core.exceptions import ValidationError
from etudiants.models import Etudiant
from .models import Examen, Repartition

class RepartitionAdminForm(forms.ModelForm):
    
    class Meta:
        model = Repartition
        fields = "__all__"
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # DON'T set queryset to none - this breaks the filter_horizontal widget
        # Instead, keep all students initially, AJAX will filter down
        self.fields['etudiants'].queryset = Etudiant.objects.all()
        
        # Customize the examen field display
        self.fields['examen'].label_from_instance = lambda obj: f"{obj.module} - {obj.get_niveau_display()} - {obj.date} ({obj.session})"

        
    def clean(self):
        cleaned_data = super().clean()
        
        examen = cleaned_data.get("examen")
        amphi = cleaned_data.get("amphi")
        surveillants = cleaned_data.get("surveillants")
        etudiants = cleaned_data.get("etudiants")
        
        if not examen:
            return cleaned_data
        
        # -----------------------------
        # ✅ 1. Surveillant conflict
        # -----------------------------
        if surveillants:
            for surveillant in surveillants:
                conflict = Repartition.objects.filter(
                    surveillants=surveillant,
                    examen__date=examen.date
                ).exclude(pk=self.instance.pk).exists()
                
                if conflict:
                    raise ValidationError(
                        f"Surveillant '{surveillant.nom}' déjà assigné à un autre examen le {examen.date}"
                    )
        
        # -----------------------------
        # ✅ 2. Amphi conflict
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
        # ✅ 3. Prevent duplicate student assignment
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