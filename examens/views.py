from collections import defaultdict
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from etudiants.models import Etudiant
from .models import Examen, Repartition, Session
from django.contrib.admin.views.decorators import staff_member_required
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from io import BytesIO
from django.db.models import Count, Q
from surveillants.models import Surveillant
import os
from django.conf import settings

def calendrier_examens(request):
    # Get filters from request
    session_id = request.GET.get('session')
    session_type = request.GET.get('type')
    
    # Start with exams from active sessions only
    if session_id:
        # If specific session selected, get that session (even if inactive)
        examens = Examen.objects.select_related("annee", "session").filter(session_id=session_id)
    elif session_type:
        # If session type selected, filter by type and only active
        examens = Examen.objects.select_related("annee", "session").filter(
            session__type=session_type, 
            session__is_active=True
        )
    else:
        # DEFAULT: Show ONLY active sessions
        examens = Examen.objects.select_related("annee", "session").filter(session__is_active=True)
    
    examens = examens.order_by("date")
    
    planning = defaultdict(list)
    for exam in examens:
        planning[exam.date].append(exam)
    
    # Show all sessions in dropdown (including inactive) but with indicator
    sessions = Session.objects.all().order_by('-date_debut')
    
    # Get current filter info for display
    filter_info = ""
    if session_id:
        session = Session.objects.get(id=session_id)
        filter_info = f"{session.nom} - {session.get_type_display()}"
    elif session_type:
        filter_info = "Rattrapage" if session_type == 'rattrapage' else "Normale"
    else:
        filter_info = "Sessions actives uniquement"
    
    context = {
        "planning": dict(planning),
        "sessions": sessions,
        "selected_session": session_id,
        "selected_type": session_type,
        "filter_info": filter_info,
    }
    
    return render(request, "examens/calendrier.html", context)

def test_view(request):
    return HttpResponse("Test view is working!")


@staff_member_required
@csrf_exempt
def get_students_by_exam(request):
    print("=== VIEW CALLED ===")
    print("GET params:", request.GET)
    
    exam_id = request.GET.get('exam_id')
    repartition_id = request.GET.get('repartition_id')
    
    print(f"exam_id: {exam_id}")
    print(f"repartition_id: {repartition_id}")
    
    if not exam_id:
        return JsonResponse({'success': False, 'error': 'No exam ID provided'})
    
    try:
        exam = Examen.objects.get(pk=exam_id)
        print(f"Found exam: {exam.module}, niveau: {exam.niveau}, annee: {exam.annee}")
        
        # Get all students for this exam
        all_students = Etudiant.objects.filter(
            niveau=exam.niveau,
            annee=exam.annee
        )
        print(f"Total students found: {all_students.count()}")
        
        # Get assigned student IDs
        assigned_repartitions = Repartition.objects.filter(examen=exam)
        if repartition_id:
            assigned_repartitions = assigned_repartitions.exclude(pk=repartition_id)
            print(f"Excluding current repartition ID: {repartition_id}")
        
        assigned_student_ids = []
        for rep in assigned_repartitions:
            rep_students = rep.etudiants.values_list('id', flat=True)
            print(f"Repartition {rep.id} has students: {list(rep_students)}")
            assigned_student_ids.extend(rep_students)
        
        assigned_student_ids = list(set(assigned_student_ids))
        print(f"All assigned student IDs: {assigned_student_ids}")
        
        # Get available students
        available_students = all_students.exclude(id__in=assigned_student_ids)
        print(f"Available students count: {available_students.count()}")
        
        students_list = list(available_students.values('id', 'nom', 'prenom', 'apogee'))
        print(f"Returning {len(students_list)} students")
        
        return JsonResponse({
            'success': True,
            'students': students_list,
            'niveau_display': exam.get_niveau_display(),
            'annee': str(exam.annee),
            'total_students': all_students.count(),
            'assigned_count': len(assigned_student_ids),
            'available_count': len(students_list)
        })
        
    except Examen.DoesNotExist:
        print(f"Exam {exam_id} not found!")
        return JsonResponse({'success': False, 'error': f'Exam with id {exam_id} not found'})
    except Exception as e:
        print(f"Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


@staff_member_required
def generate_presence_pdf(request, repartition_id):
    """Generate PDF presence list for a single repartition"""
    repartition = get_object_or_404(Repartition, pk=repartition_id)
    
    # Create PDF response - open in browser
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="presence_{repartition.examen.module}_{repartition.examen.date}.pdf"'
    
    # Create PDF document - Portrait A4
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.1*cm, bottomMargin=0.1*cm, leftMargin=1.5*cm, rightMargin=1.5*cm)
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Normal'],
        fontSize=12,
        alignment=TA_CENTER,
        spaceAfter=5,
        fontName='Helvetica-Bold'
    )
    
    # Content
    story = []
    
    # Try to add logo
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
    if os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=7*cm, height=2*cm)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 10))
        except:
            pass
    
    # Header: Faculté
    faculté_text = Paragraph("Faculté de Médecine et de Pharmacie Laâyoune", title_style)
    story.append(faculté_text)
    
    # Année Universitaire
    annee_text = Paragraph(f"<b>Année Universitaire {repartition.examen.annee}</b>", title_style)
    story.append(annee_text)
    story.append(Spacer(1, 10))
    
    # Create a bordered table for EXAMEN DU SEMESTRE and Session
    bordered_data = []
    
    # Titre EXAMEN DU SEMESTRE
    examen_title = Paragraph(f"<b>EXAMEN DU SEMESTRE, SESSION {repartition.examen.session.get_type_display().upper()}</b><b>, {repartition.examen.session.nom.upper()}</b>", 
                            ParagraphStyle('ExamenTitle', parent=styles['Normal'], fontSize=11, alignment=TA_CENTER, spaceAfter=0))
    bordered_data.append([examen_title])
    
    # Create bordered table
    bordered_table = Table(bordered_data, colWidths=[16*cm])
    bordered_table.setStyle(TableStyle([
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#0b2a53')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    story.append(bordered_table)
    story.append(Spacer(1, 15))
    
    # MODULE and DATE on the same line - MODULE left, DATE far right
    # Using 3 columns: MODULE | Spacer | DATE
    info_data = [
        [Paragraph(f"<b>MODULE :</b> {repartition.examen.module.upper()}", 
                   ParagraphStyle('ModuleText', fontSize=10, alignment=TA_LEFT)),
         "",
         Paragraph(f"<b>DATE :</b> {repartition.examen.date.strftime('%d %B %Y').upper()}", 
                   ParagraphStyle('DateText', fontSize=10, alignment=TA_RIGHT))]
    ]
    
    info_table = Table(info_data, colWidths=[8*cm, 4*cm, 4*cm])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 15))
    
    # Table title
    table_title = Paragraph("<b>Liste de Présence</b>", 
                           ParagraphStyle('TableTitle', parent=styles['Normal'], fontSize=11, alignment=TA_CENTER, spaceAfter=10))
    story.append(table_title)
    
    # Students table
    students = repartition.etudiants.all().order_by('nom', 'prenom')
    
    if students.exists():
        # Table headers
        table_data = [
            ['CODE', 'NOM ET PRENOM', 'SALLE', 'NUM', 'EMARGEMENT']
        ]
        
        # Add students
        for idx, student in enumerate(students, 1):
            table_data.append([
                student.apogee,
                f"{student.nom.upper()} {student.prenom.upper()}",
                repartition.amphi.nom,
                str(idx),
                ''
            ])
        
        # Create table - adjusted column widths for portrait
        student_table = Table(table_data, colWidths=[2.5*cm, 5.5*cm, 3.5*cm, 1.2*cm, 3.5*cm], repeatRows=1)
        student_table.setStyle(TableStyle([
            # Header style
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0b2a53")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            
            # Data style
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (3, 1), (3, -1), 'CENTER'),
            ('ALIGN', (4, 1), (4, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            
            # Row background
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            
            # Padding
            ('TOPPADDING', (0, 1), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ]))
        
        story.append(student_table)
        
        # Add footer with counts only
        story.append(Spacer(1, 15))
        
        # Total students count
        total_text = Paragraph(f"<b>Total des étudiants :</b> {students.count()}", 
                              ParagraphStyle('Total', fontSize=9, alignment=TA_LEFT))
        story.append(total_text)
        
    else:
        story.append(Paragraph("Aucun étudiant affecté à cette répartition.", styles['Normal']))
    
    # Build PDF
    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    
    return response

@staff_member_required
def generate_multiple_presence_pdf(request):
    """Generate PDF for multiple repartitions"""
    ids = request.GET.get('ids', '').split(',')
    repartitions = Repartition.objects.filter(pk__in=ids)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="presences_multiple.pdf"'
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    
    styles = getSampleStyleSheet()
    
    for idx, repartition in enumerate(repartitions):
        # Try to add logo
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=4*cm, height=4*cm)
                logo.hAlign = 'CENTER'
                story.append(logo)
                story.append(Spacer(1, 10))
            except:
                pass
        
        # Header: Faculté
        faculté_text = Paragraph("Faculté de Médecine et de Pharmacie Laâyoune", 
                                ParagraphStyle('Faculte', parent=styles['Normal'], fontSize=12, alignment=TA_CENTER, fontName='Helvetica-Bold'))
        story.append(faculté_text)
        
        # Année Universitaire
        annee_text = Paragraph(f"<b>Année Universitaire {repartition.examen.annee}</b>", 
                              ParagraphStyle('Annee', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER))
        story.append(annee_text)
        story.append(Spacer(1, 10))
        
        # Titre EXAMEN
        examen_title = Paragraph(f"<b>EXAMEN DU SEMESTRE, SESSION {repartition.examen.session.get_type_display().upper()}</b>", 
                                ParagraphStyle('ExamenTitle', parent=styles['Normal'], fontSize=11, alignment=TA_CENTER))
        story.append(examen_title)
        
        # Session
        session_text = Paragraph(f"<b>Session {repartition.examen.session.nom}</b>", 
                                ParagraphStyle('SessionText', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER, spaceAfter=15))
        story.append(session_text)
        
        # Date
        date_text = Paragraph(f"<b>DATE :</b> {repartition.examen.date.strftime('%d %B %Y').upper()}", 
                             ParagraphStyle('DateText', parent=styles['Normal'], fontSize=10, alignment=TA_LEFT, spaceAfter=10))
        story.append(date_text)
        
        # Module
        module_text = Paragraph(f"<b>MODULE :</b> {repartition.examen.module.upper()}", 
                               ParagraphStyle('ModuleText', parent=styles['Normal'], fontSize=10, alignment=TA_LEFT, spaceAfter=15))
        story.append(module_text)
        
        # Table title
        table_title = Paragraph("<b>Liste de Présence</b>", 
                               ParagraphStyle('TableTitle', parent=styles['Normal'], fontSize=11, alignment=TA_CENTER, spaceAfter=10))
        story.append(table_title)
        
        # Students table
        students = repartition.etudiants.all().order_by('nom', 'prenom')
        if students.exists():
            table_data = [['CODE', 'NOM ET PRENOM', 'SALLE', 'NUM', 'EMARGEMENT']]
            for student_idx, student in enumerate(students, 1):
                table_data.append([
                    student.apogee,
                    f"{student.nom.upper()} {student.prenom.upper()}",
                    repartition.amphi.nom,
                    str(student_idx),
                    ''
                ])
            
            student_table = Table(table_data, colWidths=[2.5*cm, 5.5*cm, 3.5*cm, 1.2*cm, 3.5*cm], repeatRows=1)
            student_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a472a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),
                ('ALIGN', (4, 1), (4, -1), 'CENTER'),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(student_table)
            story.append(Spacer(1, 10))
            story.append(Paragraph(f"<b>Total des étudiants :</b> {students.count()}", 
                                  ParagraphStyle('Total', fontSize=9)))
        else:
            story.append(Paragraph("Aucun étudiant affecté", styles['Normal']))
        
        # Add page break except for the last repartition
        if idx < len(repartitions) - 1:
            story.append(PageBreak())
    
    # Build PDF
    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    
    return response


# examens/views.py - Ajoutez ces fonctions

@staff_member_required
def convocations_list(request):
    """Liste des convocations des surveillants avec filtres"""
    from surveillants.models import Surveillant
    
    # Get filter parameters
    session_id = request.GET.get('session')
    
    # Get all sessions for filter dropdown
    sessions = Session.objects.filter(is_active=True).order_by('-date_debut')
    
    # Get all surveillant IDs that have repartitions
    if session_id:
        selected_session = Session.objects.get(id=session_id)
        # Get repartitions for this session
        repartitions = Repartition.objects.filter(examen__session_id=session_id)
        surveillant_ids = set()
        for rep in repartitions:
            for surv in rep.surveillants.all():
                surveillant_ids.add(surv.id)
        surveillant_ids = list(surveillant_ids)
    else:
        selected_session = None
        # Get all repartitions
        repartitions = Repartition.objects.all()
        surveillant_ids = set()
        for rep in repartitions:
            for surv in rep.surveillants.all():
                surveillant_ids.add(surv.id)
        surveillant_ids = list(surveillant_ids)
    
    # Get surveillants
    surveillants = Surveillant.objects.filter(id__in=surveillant_ids).order_by('nom')
    
    # Add examens_count to each surveillant
    for surveillant in surveillants:
        if session_id:
            count = Repartition.objects.filter(
                surveillants=surveillant,
                examen__session_id=session_id
            ).count()
        else:
            count = Repartition.objects.filter(surveillants=surveillant).count()
        surveillant.examens_count = count
    
    context = {
        'sessions': sessions,
        'surveillants': surveillants,
        'selected_session': selected_session,
        'session_id': session_id,
    }
    
    return render(request, 'examens/convocations_list.html', context)

@staff_member_required
def generate_convocation_pdf(request, surveillant_id, session_id=None):
    """Generate convocation PDF for a specific surveillant and session"""
    from surveillants.models import Surveillant
    
    surveillant = get_object_or_404(Surveillant, pk=surveillant_id)
    
    # Get repartitions for this surveillant - CORRECTED
    # On filtre les Repartition qui contiennent ce surveillant
    repartitions = Repartition.objects.filter(surveillants=surveillant)
    
    # Filter by session if provided
    session_name = None
    if session_id:
        repartitions = repartitions.filter(examen__session_id=session_id)
        session = get_object_or_404(Session, pk=session_id)
        session_name = session.nom
    else:
        # Get the most recent session
        latest_repartition = repartitions.order_by('examen__session__date_debut').first()
        if latest_repartition:
            session_name = latest_repartition.examen.session.nom
    
    repartitions = repartitions.order_by('examen__date', 'examen__heure_debut')
    
    # Create PDF response
    response = HttpResponse(content_type='application/pdf')
    filename = f"convocation_{surveillant.nom}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    
    # Create PDF document
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm, leftMargin=2*cm, rightMargin=2*cm)
    
    # Styles
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=5,
        textColor=colors.HexColor("#081B35"),
        fontName='Helvetica-Bold'
    )
    
    # Subtitle style
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=10,
        textColor=colors.HexColor("#081B35"),
        fontName='Helvetica-Bold'
    )
    
    # Attention style
    attention_style = ParagraphStyle(
        'AttentionStyle',
        parent=styles['Normal'],
        fontSize=11,
        alignment=TA_CENTER,
        spaceAfter=15,
        fontName='Helvetica-Bold'
    )
    
    # Body text style
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_JUSTIFY,
        spaceAfter=15,
        leading=14
    )
    
    # Footer style
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=9,
        alignment=TA_LEFT,
        spaceAfter=5
    )
    
    # Content
    story = []
    
    # Logo
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
    if os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=8*cm, height=2*cm)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(10, 20))
        except:
            pass
    
    # Title
    title = Paragraph("CONVOCATION À LA SURVEILLANCE DES EXAMENS", title_style)
    story.append(title)
    
    # Session subtitle
    if session_name:
        subtitle = Paragraph(f"SESSION {session_name.upper()}", subtitle_style)
    else:
        subtitle = Paragraph("SESSION EN COURS", subtitle_style)
    story.append(subtitle)
    
    story.append(Spacer(1, 10))
    
    # Attention line
    attention_text = Paragraph(f"<b>A l'attention de :</b> {surveillant.specialite.upper()} {surveillant.nom.upper()}", attention_style)
    story.append(attention_text)
    
    story.append(Spacer(1, 5))
    
    # Body text
    body_text = """
    La doyenne de la Faculté de Médecine de Pharmacie Laâyoune, vous informe que vous avez été désigné(e) 
    pour assurer la surveillance lors des prochains examens qui auront lieu dans notre faculté.
    """
    story.append(Paragraph(body_text, body_style))
    
    story.append(Paragraph("<b>Vous trouverez ci-dessous les détails de la surveillance :</b>", body_style))
    story.append(Spacer(1, 10))
    
    # Exams table
    if repartitions.exists():
        table_data = [
            ['Date et heure d\'examen', 'Matière', 'Amphi / Salle']
        ]
        
        for rep in repartitions:
            exam = rep.examen
            date_time = f"{exam.date.strftime('%d/%m/%Y')} – {exam.heure_debut.strftime('%H:%M')} – {exam.heure_fin.strftime('%H:%M')}"
            table_data.append([
                date_time,
                exam.module,
                rep.amphi.nom
            ])
        
        # Create table
        exam_table = Table(table_data, colWidths=[4.5*cm, 6.5*cm, 4*cm], repeatRows=1)
        exam_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#10327c")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]))
        
        story.append(exam_table)
        story.append(Spacer(1, 15))
        
        # Note for force majeure
        note_text = """
        <i>Si pour une raison de force majeure vous vous trouviez dans l'impossibilité d'assurer cette mission, 
        il vous appartiendrait d'en aviser immédiatement par téléphone l'administration de la faculté.</i>
        """
        story.append(Paragraph(note_text, body_style))
        
        story.append(Spacer(1, 15))
        
        # Thank you note
        thanks_text = "<b>Nous tenons à vous remercier d'avance pour votre collaboration.</b>"
        story.append(Paragraph(thanks_text, body_style))
        
        story.append(Spacer(1, 25))
        
         # Cache
    cache_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'Cache.png')
    if os.path.exists(cache_path):
        try:
            cache = Image(cache_path, width=5*cm, height=5*cm)
            cache.hAlign = 'CENTER'
            story.append(cache)
            story.append(Spacer(1, 10))
        except:
            pass
        
       
    
    # Build PDF
    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    
    return response

@staff_member_required
def convocation_bulk_pdf(request):
    """Generate bulk convocations ZIP for selected surveillants"""
    surveillant_ids = request.GET.get('ids', '')
    session_id = request.GET.get('session')
    
    from surveillants.models import Surveillant
    
    # Filtrer les IDs vides ou None
    if surveillant_ids:
        surveillant_ids = [id for id in surveillant_ids.split(',') if id and id.strip()]
    else:
        surveillant_ids = []
    
    # Vérifier qu'on a des IDs valides
    if not surveillant_ids:
        from django.contrib import messages
        from django.shortcuts import redirect
        messages.error(request, "Aucun surveillant sélectionné.")
        return redirect('examens:convocations_list')
    
    # Convertir en entiers et ignorer les valeurs None
    valid_ids = []
    for id_str in surveillant_ids:
        try:
            valid_ids.append(int(id_str))
        except ValueError:
            continue
    
    if not valid_ids:
        messages.error(request, "IDs de surveillants invalides.")
        return redirect('examens:convocations_list')
    
    surveillants = Surveillant.objects.filter(id__in=valid_ids)
    
    if not surveillants.exists():
        messages.error(request, "Aucun surveillant trouvé avec les IDs sélectionnés.")
        return redirect('examens:convocations_list')
    
    import zipfile
    from io import BytesIO
    
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for surveillant in surveillants:
            # Generate PDF for each surveillant
            pdf_buffer = BytesIO()
            
            # Get repartitions for this surveillant
            repartitions = Repartition.objects.filter(surveillants=surveillant)
            if session_id and session_id != 'None' and session_id.strip():
                try:
                    session_id_int = int(session_id)
                    repartitions = repartitions.filter(examen__session_id=session_id_int)
                    session = get_object_or_404(Session, pk=session_id_int)
                    session_name = session.nom
                except ValueError:
                    session_name = None
            else:
                # Get the most recent session
                latest_repartition = repartitions.order_by('examen__session__date_debut').first()
                if latest_repartition:
                    session_name = latest_repartition.examen.session.nom
                else:
                    session_name = None
            
            repartitions = repartitions.order_by('examen__date', 'examen__heure_debut')
            
            # Create PDF document - A4 Portrait
            doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm, leftMargin=2*cm, rightMargin=2*cm)
            styles = getSampleStyleSheet()
            
            # Styles
            title_style = ParagraphStyle(
                'TitleStyle',
                parent=styles['Heading1'],
                fontSize=16,
                alignment=TA_CENTER,
                spaceAfter=5,
                textColor=colors.HexColor("#081B35"),
                fontName='Helvetica-Bold'
            )
            
            subtitle_style = ParagraphStyle(
                'SubtitleStyle',
                parent=styles['Heading1'],
                fontSize=16,
                alignment=TA_CENTER,
                spaceAfter=10,
                textColor=colors.HexColor("#081B35"),
                fontName='Helvetica-Bold'
            )
            
            attention_style = ParagraphStyle(
                'AttentionStyle',
                parent=styles['Normal'],
                fontSize=11,
                alignment=TA_CENTER,
                spaceAfter=15,
                fontName='Helvetica-Bold'
            )
            
            body_style = ParagraphStyle(
                'BodyStyle',
                parent=styles['Normal'],
                fontSize=10,
                alignment=TA_JUSTIFY,
                spaceAfter=15,
                leading=14
            )
            
            # Content
            story = []
            
            # Logo
            logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
            if os.path.exists(logo_path):
                try:
                    logo = Image(logo_path, width=8*cm, height=2*cm)
                    logo.hAlign = 'CENTER'
                    story.append(logo)
                    story.append(Spacer(10, 20))
                except:
                    pass
            
            # Title
            title = Paragraph("CONVOCATION À LA SURVEILLANCE DES EXAMENS", title_style)
            story.append(title)
            
            # Session subtitle
            if session_name:
                subtitle = Paragraph(f"SESSION {session_name.upper()}", subtitle_style)
            else:
                subtitle = Paragraph("SESSION EN COURS", subtitle_style)
            story.append(subtitle)
            
            story.append(Spacer(1, 10))
            
            # Attention line
            specialite = surveillant.specialite.upper() if surveillant.specialite else ""
            attention_text = Paragraph(f"<b>A l'attention de :</b> {specialite} {surveillant.nom.upper()}", attention_style)
            story.append(attention_text)
            
            story.append(Spacer(1, 5))
            
            # Body text
            body_text = """
            La doyenne de la Faculté de Médecine de Pharmacie Laâyoune, vous informe que vous avez été désigné(e) 
            pour assurer la surveillance lors des prochains examens qui auront lieu dans notre faculté.
            """
            story.append(Paragraph(body_text, body_style))
            
            story.append(Paragraph("<b>Vous trouverez ci-dessous les détails de la surveillance :</b>", body_style))
            story.append(Spacer(1, 10))
            
            # Exams table
            if repartitions.exists():
                table_data = [
                    ['Date et heure d\'examen', 'Matière', 'Amphi / Salle']
                ]
                
                for rep in repartitions:
                    exam = rep.examen
                    date_time = f"{exam.date.strftime('%d/%m/%Y')} – {exam.heure_debut.strftime('%H:%M')} – {exam.heure_fin.strftime('%H:%M')}"
                    table_data.append([
                        date_time,
                        exam.module,
                        rep.amphi.nom
                    ])
                
                # Create table
                exam_table = Table(table_data, colWidths=[4.5*cm, 6.5*cm, 4*cm], repeatRows=1)
                exam_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#10327c")),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('TOPPADDING', (0, 0), (-1, 0), 8),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('ALIGN', (0, 1), (0, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                    ('TOPPADDING', (0, 1), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
                    ('LEFTPADDING', (0, 0), (-1, -1), 5),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ]))
                
                story.append(exam_table)
                story.append(Spacer(1, 15))
                
                # Note for force majeure
                note_text = """
                <i>Si pour une raison de force majeure vous vous trouviez dans l'impossibilité d'assurer cette mission, 
                il vous appartiendrait d'en aviser immédiatement par téléphone l'administration de la faculté.</i>
                """
                story.append(Paragraph(note_text, body_style))
                
                story.append(Spacer(1, 15))
                
                # Thank you note
                thanks_text = "<b>Nous tenons à vous remercier d'avance pour votre collaboration.</b>"
                story.append(Paragraph(thanks_text, body_style))
                
                story.append(Spacer(1, 25))
                
                # Cache image
                cache_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'Cache.png')
                if os.path.exists(cache_path):
                    try:
                        cache = Image(cache_path, width=5*cm, height=5*cm)
                        cache.hAlign = 'CENTER'
                        story.append(cache)
                        story.append(Spacer(1, 10))
                    except:
                        pass
            
            else:
                story.append(Paragraph("Aucune surveillance programmée pour ce surveillant.", styles['Normal']))
            
            # Build PDF
            doc.build(story)
            pdf_buffer.seek(0)
            
            # Add to zip
            filename = f"convocation_{surveillant.nom}.pdf"
            zip_file.writestr(filename, pdf_buffer.getvalue())
            pdf_buffer.close()
    
    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="convocations_surveillants.zip"'
    
    return response