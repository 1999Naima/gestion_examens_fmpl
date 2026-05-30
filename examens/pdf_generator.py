# examens/pdf_generator.py
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from datetime import datetime

class ProcesVerbalPDF:
    def __init__(self, repartition):
        self.repartition = repartition
        self.examen = repartition.examen
        self.amphi = repartition.amphi
        self.session = self.examen.session
        self.students = repartition.etudiants.all()
        self.surveillants = repartition.surveillants.all()
        
    def generate(self, response):
        """Generate the complete Proces Verbal PDF (3 pages combined)"""
        pdf = canvas.Canvas(response, pagesize=A4)
        width, height = A4
        
        # PAGE 1 - First style (Header + Stats)
        self.draw_page_one(pdf, width, height)
        pdf.showPage()
        
        # PAGE 2 - Second style (Décharge with table)
        self.draw_page_two(pdf, width, height)
        pdf.showPage()
        
        # PAGE 3 - Third style (Full Proces Verbal)
        self.draw_page_three(pdf, width, height)
        
        pdf.save()
        return response
    
    def draw_page_one(self, pdf, width, height):
        """First page - Main header + Stats"""
        y = height - 50
        
        # University name
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawCentredString(width/2, y, "Faculté de Médecine et de Pharmacie Laâyoune")
        pdf.setFont("Helvetica", 12)
        pdf.drawCentredString(width/2, y - 20, f"Année Universitaire {self.examen.annee}")
        
        # Title
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawCentredString(width/2, y - 55, "PROCES VERBAL DES EPREUVES ECRITES")
        
        # Subtitle
        session_type = "NORMALE" if self.session.type == "normal" else "RATTRAPAGE"
        pdf.setFont("Helvetica", 11)
        pdf.drawCentredString(width/2, y - 75, f"Evaluations du SEMESTRE 5 SESSION {session_type.upper()}")
        
        # Date
        exam_date = self.examen.date.strftime("%d %B %Y").upper()
        pdf.drawCentredString(width/2, y - 95, exam_date)
        
        # Room
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(80, y - 130, "SALLE :")
        pdf.setFont("Helvetica", 11)
        pdf.drawString(150, y - 130, self.amphi.nom)
        
        # Module
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(80, y - 155, "Module :")
        pdf.setFont("Helvetica", 11)
        pdf.drawString(150, y - 155, self.examen.module)
        
        # Statistics table
        self.draw_stats_table(pdf, width, y - 190)
        
        # Footer
        pdf.setFont("Helvetica", 9)
        today = datetime.now().strftime("%d/%m/%Y")
        pdf.drawString(80, 50, f"Laâyoune le: {today}")
    
    def draw_stats_table(self, pdf, width, y):
        """Draw the statistics table"""
        total_students = self.students.count()
        participants = total_students
        absents = 0
        duration = f"{self.examen.heure_fin.hour - self.examen.heure_debut.hour}h"
        
        # Table headers
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(50, y, "Épreuve")
        pdf.drawString(200, y, "Nombre des candidats inscrits")
        pdf.drawString(350, y, "Nombre des participants")
        pdf.drawString(470, y, "Nombre des Absents")
        pdf.drawString(550, y, "Durée de l'épreuve")
        
        # Line under headers
        pdf.line(50, y - 5, width - 50, y - 5)
        
        # Data
        pdf.setFont("Helvetica", 10)
        module_text = self.examen.module[:30]
        pdf.drawString(50, y - 25, module_text)
        pdf.drawString(200, y - 25, str(total_students))
        pdf.drawString(350, y - 25, str(participants))
        pdf.drawString(470, y - 25, str(absents))
        pdf.drawString(550, y - 25, duration)
        
        # Bottom line
        pdf.line(50, y - 35, width - 50, y - 35)
    
    def draw_page_two(self, pdf, width, height):
        """Second page - Décharge style with table"""
        y = height - 50
        
        # University name
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawCentredString(width/2, y, "FACULTE DE MEDECINE ET DE PHARMACIE - LAÂYOUNE")
        
        # Title
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawCentredString(width/2, y - 35, "Décharge")
        
        # Exam info
        session_type = "NORMALE" if self.session.type == "normal" else "RATTRAPAGE"
        pdf.setFont("Helvetica", 11)
        pdf.drawString(50, y - 70, f"EXAMEN DU SEMESTRE, SESSION {session_type.upper()}")
        
        exam_date = self.examen.date.strftime("%d %B %Y").upper()
        pdf.drawString(50, y - 90, f"SESSION {exam_date}")
        
        # Module
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(50, y - 115, "Module :")
        pdf.setFont("Helvetica", 11)
        pdf.drawString(120, y - 115, self.examen.module)
        
        # Room
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(50, y - 140, "Salle :")
        pdf.setFont("Helvetica", 11)
        pdf.drawString(120, y - 140, self.amphi.nom)
        
        # Statistics table
        self.draw_decharge_table(pdf, width, y - 180)
        
        # Supervisors table (empty for signatures)
        self.draw_supervisors_table(pdf, width, y - 320)
        
        # Footer
        today = datetime.now().strftime("%d/%m/%Y")
        pdf.setFont("Helvetica", 10)
        pdf.drawString(50, 50, f"Laâyoune le: {today}")
    
    def draw_decharge_table(self, pdf, width, y):
        """Draw the décharge statistics table"""
        total_students = self.students.count()
        participants = total_students
        absents = 0
        duration = f"{self.examen.heure_fin.hour - self.examen.heure_debut.hour}h"
        
        # Headers
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(50, y, "Épreuve")
        pdf.drawString(180, y, "Nombre des candidats inscrits")
        pdf.drawString(330, y, "Nombre des participants")
        pdf.drawString(470, y, "Nombre des Absents")
        pdf.drawString(550, y, "Durée")
        
        pdf.line(50, y - 5, width - 50, y - 5)
        
        # Data
        pdf.setFont("Helvetica", 10)
        module_text = self.examen.module[:25]
        pdf.drawString(50, y - 25, module_text)
        pdf.drawString(180, y - 25, str(total_students))
        pdf.drawString(330, y - 25, str(participants))
        pdf.drawString(470, y - 25, str(absents))
        pdf.drawString(550, y - 25, duration)
        
        pdf.line(50, y - 35, width - 50, y - 35)
    
    def draw_supervisors_table(self, pdf, width, y):
        """Draw empty supervisors table for signatures (no names)"""
        # Headers
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(50, y, "Matière")
        pdf.drawString(180, y, "Noms & prénoms des surveillants")
        pdf.drawString(380, y, "Signatures")
        pdf.drawString(480, y, "Observations")
        
        pdf.line(50, y - 5, width - 50, y - 5)
        
        # Empty rows for signatures (3 rows)
        y_pos = y - 25
        for i in range(3):
            pdf.setFont("Helvetica", 10)
            if i == 0:
                pdf.drawString(50, y_pos, self.examen.module[:15])
            pdf.drawString(180, y_pos, "")
            pdf.drawString(380, y_pos, "")
            pdf.drawString(480, y_pos, "")
            y_pos -= 20
        
        pdf.line(50, y_pos - 5, width - 50, y_pos - 5)
    
    def draw_page_three(self, pdf, width, height):
        """Third page - Full Proces Verbal with signature lines"""
        y = height - 50
        
        # University name
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawCentredString(width/2, y, "FACULTE DE MEDECINE ET DE PHARMACIE - LAÂYOUNE")
        
        # Title
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawCentredString(width/2, y - 35, "PROCES VERBAL DES EPREUVES ECRITES")
        
        # Subtitle
        session_type = "NORMALE" if self.session.type == "normal" else "RATTRAPAGE"
        pdf.setFont("Helvetica", 11)
        pdf.drawCentredString(width/2, y - 60, f"EXAMEN DU SEMESTRE, SESSION {session_type.upper()}")
        
        exam_date = self.examen.date.strftime("%B %Y").upper()
        pdf.drawCentredString(width/2, y - 80, exam_date)
        
        # Module
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(50, y - 115, "Module :")
        pdf.setFont("Helvetica", 11)
        pdf.drawString(130, y - 115, self.examen.module)
        
        # Room
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(50, y - 140, "Salle :")
        pdf.setFont("Helvetica", 11)
        pdf.drawString(130, y - 140, self.amphi.nom)
        
        # Statistics table (compact version)
        self.draw_compact_stats(pdf, width, y - 180)
        
        # Supervisors table with empty signature lines
        self.draw_supervisors_full(pdf, width, y - 280)
        
        # Signature section
        self.draw_signatures(pdf, width, 120)
    
    def draw_compact_stats(self, pdf, width, y):
        """Compact statistics table"""
        total_students = self.students.count()
        participants = total_students
        absents = 0
        duration = f"{self.examen.heure_fin.hour - self.examen.heure_debut.hour}h"
        
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(50, y, "Épreuve")
        pdf.drawString(200, y, "Inscrits")
        pdf.drawString(300, y, "Participants")
        pdf.drawString(400, y, "Absents")
        pdf.drawString(500, y, "Durée")
        
        pdf.line(50, y - 5, width - 50, y - 5)
        
        pdf.setFont("Helvetica", 10)
        pdf.drawString(50, y - 25, self.examen.module[:25])
        pdf.drawString(200, y - 25, str(total_students))
        pdf.drawString(300, y - 25, str(participants))
        pdf.drawString(400, y - 25, str(absents))
        pdf.drawString(500, y - 25, duration)
        
        pdf.line(50, y - 35, width - 50, y - 35)
    
    def draw_supervisors_full(self, pdf, width, y):
        """Draw supervisors table with empty signature lines (no names)"""
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(50, y, "Matière")
        pdf.drawString(180, y, "Noms & prénoms des surveillants")
        pdf.drawString(380, y, "Signatures")
        pdf.drawString(480, y, "Observations")
        
        pdf.line(50, y - 5, width - 50, y - 5)
        
        # Empty rows for signatures (3 rows)
        y_pos = y - 25
        for i in range(3):
            pdf.setFont("Helvetica", 10)
            if i == 0:
                pdf.drawString(50, y_pos, self.examen.module[:15])
            pdf.drawString(180, y_pos, "")
            # Signature space (line)
            pdf.line(380, y_pos - 5, 470, y_pos - 5)
            pdf.drawString(480, y_pos, "")
            y_pos -= 20
        
        pdf.line(50, y_pos - 5, width - 50, y_pos - 5)
    
    def draw_signatures(self, pdf, width, y):
        """Draw signature section at bottom"""
        # Signature lines
        pdf.line(50, y + 50, 180, y + 50)
        pdf.setFont("Helvetica", 9)
        pdf.drawCentredString(115, y + 40, "Le Surveillant")
        
        pdf.line(width - 180, y + 50, width - 50, y + 50)
        pdf.drawCentredString(width - 115, y + 40, "Le Doyen")
        
        pdf.line(width/2 - 65, y + 50, width/2 + 65, y + 50)
        pdf.drawCentredString(width/2, y + 40, "Le Chef de Département")