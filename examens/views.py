from collections import defaultdict
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render, get_object_or_404
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
from django.core.mail import EmailMessage
from django.conf import settings as django_settings
from django.contrib import admin

# ── Mois en français (évite la dépendance à la locale système) ───────────────
MOIS_FR = {
    1: "janvier",  2: "février",  3: "mars",     4: "avril",
    5: "mai",      6: "juin",     7: "juillet",  8: "août",
    9: "septembre",10: "octobre", 11: "novembre",12: "décembre"
}

def date_fr(d):
    """Retourne une date formatée en français : '11 juin 2026'"""
    return f"{d.day:02d} {MOIS_FR[d.month]} {d.year}"


# ─────────────────────────────────────────────────────────────────
# CALENDRIER
# ─────────────────────────────────────────────────────────────────
def calendrier_examens(request):
    session_id   = request.GET.get('session')
    session_type = request.GET.get('type')

    if session_id:
        examens = Examen.objects.select_related("annee", "session").filter(session_id=session_id)
    elif session_type:
        examens = Examen.objects.select_related("annee", "session").filter(
            session__type=session_type,
            session__is_active=True
        )
    else:
        examens = Examen.objects.select_related("annee", "session").filter(session__is_active=True)

    examens = examens.order_by("date")

    planning = defaultdict(list)
    for exam in examens:
        planning[exam.date].append(exam)

    sessions = Session.objects.all().order_by('-date_debut')

    filter_info = ""
    if session_id:
        session = Session.objects.get(id=session_id)
        filter_info = f"{session.nom} - {session.get_type_display()}"
    elif session_type:
        filter_info = "Rattrapage" if session_type == 'rattrapage' else "Normale"
    else:
        filter_info = "Sessions actives uniquement"

    context = {
        "planning":        dict(planning),
        "sessions":        sessions,
        "selected_session": session_id,
        "selected_type":   session_type,
        "filter_info":     filter_info,
    }
    return render(request, "examens/calendrier.html", context)


def test_view(request):
    return HttpResponse("Test view is working!")


# ─────────────────────────────────────────────────────────────────
# AJAX : étudiants par examen
# ─────────────────────────────────────────────────────────────────
@staff_member_required
@csrf_exempt
def get_students_by_exam(request):
    exam_id        = request.GET.get('exam_id')
    repartition_id = request.GET.get('repartition_id')

    if not exam_id:
        return JsonResponse({'success': False, 'error': 'No exam ID provided'})

    try:
        exam         = Examen.objects.get(pk=exam_id)
        all_students = Etudiant.objects.filter(niveau=exam.niveau, annee=exam.annee)

        assigned_repartitions = Repartition.objects.filter(examen=exam)
        if repartition_id:
            assigned_repartitions = assigned_repartitions.exclude(pk=repartition_id)

        assigned_student_ids = []
        for rep in assigned_repartitions:
            assigned_student_ids.extend(rep.etudiants.values_list('id', flat=True))
        assigned_student_ids = list(set(assigned_student_ids))

        available_students = all_students.exclude(id__in=assigned_student_ids)
        students_list      = list(available_students.values('id', 'nom', 'prenom', 'apogee'))

        return JsonResponse({
            'success':        True,
            'students':       students_list,
            'niveau_display': exam.get_niveau_display(),
            'annee':          str(exam.annee),
            'total_students': all_students.count(),
            'assigned_count': len(assigned_student_ids),
            'available_count': len(students_list),
        })

    except Examen.DoesNotExist:
        return JsonResponse({'success': False, 'error': f'Exam with id {exam_id} not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ─────────────────────────────────────────────────────────────────
# LISTE DE PRÉSENCE (une répartition)
# ─────────────────────────────────────────────────────────────────
@staff_member_required
def generate_presence_pdf(request, repartition_id):
    repartition = get_object_or_404(Repartition, pk=repartition_id)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'inline; filename="presence_{repartition.examen.module}_{repartition.examen.date}.pdf"'
    )

    buffer = BytesIO()
    doc    = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=0.1*cm, bottomMargin=0.1*cm,
        leftMargin=1.5*cm, rightMargin=1.5*cm
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Normal'],
        fontSize=12, alignment=TA_CENTER, spaceAfter=5, fontName='Helvetica-Bold'
    )

    story = []

    # Logo
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
    if os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=7*cm, height=2*cm)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 10))
        except Exception:
            pass

    # En-tête
    story.append(Paragraph("Faculté de Médecine et de Pharmacie Laâyoune", title_style))
    story.append(Paragraph(f"<b>Année Universitaire {repartition.examen.annee}</b>", title_style))
    story.append(Spacer(1, 10))

    # Bloc session (encadré)
    examen_title = Paragraph(
        f"<b>EXAMEN DU SEMESTRE {repartition.examen.semester}, SESSION "
        f"{repartition.examen.session.get_type_display().upper()}</b>"
        f"<b>, {repartition.examen.session.nom.upper()}</b>",
        ParagraphStyle('ExamenTitle', parent=styles['Normal'],
                       fontSize=11, alignment=TA_CENTER, spaceAfter=0)
    )
    bordered_table = Table([[examen_title]], colWidths=[16*cm])
    bordered_table.setStyle(TableStyle([
        ('BOX',           (0, 0), (-1, -1), 1.5, colors.HexColor('#0b2a53')),
        ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING',   (0, 0), (-1, -1), 10),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 10),
    ]))
    story.append(bordered_table)
    story.append(Spacer(1, 15))

    # MODULE | DATE sur la même ligne  ← date_fr() ici
    info_data = [[
        Paragraph(
            f"<b>MODULE :</b> {repartition.examen.module.upper()}",
            ParagraphStyle('ModuleText', fontSize=10, alignment=TA_LEFT)
        ),
        "",
        Paragraph(
            f"<b>DATE :</b> {date_fr(repartition.examen.date).upper()}",
            ParagraphStyle('DateText', fontSize=10, alignment=TA_RIGHT)
        ),
    ]]
    info_table = Table(info_data, colWidths=[8*cm, 4*cm, 4*cm])
    info_table.setStyle(TableStyle([
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',    (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING',   (0, 0), (-1, -1), 0),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 15))

    # Titre liste
    story.append(Paragraph(
        "<b>Liste de Présence</b>",
        ParagraphStyle('TableTitle', parent=styles['Normal'],
                       fontSize=11, alignment=TA_CENTER, spaceAfter=10)
    ))

    # Tableau étudiants
    students = repartition.etudiants.all().order_by('nom', 'prenom')
    if students.exists():
        table_data = [['CODE', 'NOM ET PRENOM', 'SALLE', 'NUM', 'EMARGEMENT']]
        for idx, student in enumerate(students, 1):
            table_data.append([
                student.apogee,
                f"{student.nom.upper()} {student.prenom.upper()}",
                repartition.amphi.nom,
                str(idx),
                '',
            ])

        student_table = Table(
            table_data,
            colWidths=[2.5*cm, 5.5*cm, 3.5*cm, 1.2*cm, 3.5*cm],
            repeatRows=1
        )
        student_table.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor("#0b2a53")),
            ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
            ('ALIGN',         (0, 0), (-1, 0),  'CENTER'),
            ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
            ('FONTSIZE',      (0, 0), (-1, 0),  9),
            ('BOTTOMPADDING', (0, 0), (-1, 0),  8),
            ('TOPPADDING',    (0, 0), (-1, 0),  8),
            ('FONTNAME',      (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE',      (0, 1), (-1, -1), 8),
            ('ALIGN',         (0, 1), (0,  -1), 'CENTER'),
            ('ALIGN',         (3, 1), (3,  -1), 'CENTER'),
            ('ALIGN',         (4, 1), (4,  -1), 'CENTER'),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('ROWBACKGROUNDS',(0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
            ('TOPPADDING',    (0, 1), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
            ('LEFTPADDING',   (0, 0), (-1, -1), 3),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 3),
        ]))
        story.append(student_table)
        story.append(Spacer(1, 15))
        story.append(Paragraph(
            f"<b>Total des étudiants :</b> {students.count()}",
            ParagraphStyle('Total', fontSize=9, alignment=TA_LEFT)
        ))
    else:
        story.append(Paragraph("Aucun étudiant affecté à cette répartition.", styles['Normal']))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response


# ─────────────────────────────────────────────────────────────────
# LISTE DE PRÉSENCE (plusieurs répartitions)
# ─────────────────────────────────────────────────────────────────
@staff_member_required
def generate_multiple_presence_pdf(request):
    ids          = request.GET.get('ids', '').split(',')
    repartitions = Repartition.objects.filter(pk__in=ids)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="presences_multiple.pdf"'

    buffer = BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=A4)
    story  = []
    styles = getSampleStyleSheet()

    for idx, repartition in enumerate(repartitions):
        # Logo
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
        if os.path.exists(logo_path):
            try:
                logo = Image(logo_path, width=4*cm, height=4*cm)
                logo.hAlign = 'CENTER'
                story.append(logo)
                story.append(Spacer(1, 10))
            except Exception:
                pass

        story.append(Paragraph(
            "Faculté de Médecine et de Pharmacie Laâyoune",
            ParagraphStyle('Faculte', parent=styles['Normal'],
                           fontSize=12, alignment=TA_CENTER, fontName='Helvetica-Bold')
        ))
        story.append(Paragraph(
            f"<b>Année Universitaire {repartition.examen.annee}</b>",
            ParagraphStyle('Annee', parent=styles['Normal'],
                           fontSize=10, alignment=TA_CENTER)
        ))
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            f"<b>EXAMEN DU SEMESTRE {repartition.examen.semester}, SESSION "
            f"{repartition.examen.session.get_type_display().upper()}</b>",
            ParagraphStyle('ExamenTitle', parent=styles['Normal'],
                           fontSize=11, alignment=TA_CENTER)
        ))
        story.append(Paragraph(
            f"<b>Session {repartition.examen.session.nom}</b>",
            ParagraphStyle('SessionText', parent=styles['Normal'],
                           fontSize=10, alignment=TA_CENTER, spaceAfter=15)
        ))

        # ← date_fr() ici
        story.append(Paragraph(
            f"<b>DATE :</b> {date_fr(repartition.examen.date).upper()}",
            ParagraphStyle('DateText', parent=styles['Normal'],
                           fontSize=10, alignment=TA_LEFT, spaceAfter=10)
        ))
        story.append(Paragraph(
            f"<b>MODULE :</b> {repartition.examen.module.upper()}",
            ParagraphStyle('ModuleText', parent=styles['Normal'],
                           fontSize=10, alignment=TA_LEFT, spaceAfter=15)
        ))
        story.append(Paragraph(
            "<b>Liste de Présence</b>",
            ParagraphStyle('TableTitle', parent=styles['Normal'],
                           fontSize=11, alignment=TA_CENTER, spaceAfter=10)
        ))

        students = repartition.etudiants.all().order_by('nom', 'prenom')
        if students.exists():
            table_data = [['CODE', 'NOM ET PRENOM', 'SALLE', 'NUM', 'EMARGEMENT']]
            for student_idx, student in enumerate(students, 1):
                table_data.append([
                    student.apogee,
                    f"{student.nom.upper()} {student.prenom.upper()}",
                    repartition.amphi.nom,
                    str(student_idx),
                    '',
                ])

            student_table = Table(
                table_data,
                colWidths=[2.5*cm, 5.5*cm, 3.5*cm, 1.2*cm, 3.5*cm],
                repeatRows=1
            )
            student_table.setStyle(TableStyle([
                ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor('#1a472a')),
                ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
                ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
                ('FONTSIZE',      (0, 0), (-1, 0),  9),
                ('GRID',          (0, 0), (-1, -1), 0.5, colors.black),
                ('FONTSIZE',      (0, 1), (-1, -1), 8),
                ('ALIGN',         (0, 1), (0,  -1), 'CENTER'),
                ('ALIGN',         (3, 1), (3,  -1), 'CENTER'),
                ('ALIGN',         (4, 1), (4,  -1), 'CENTER'),
                ('TOPPADDING',    (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(student_table)
            story.append(Spacer(1, 10))
            story.append(Paragraph(
                f"<b>Total des étudiants :</b> {students.count()}",
                ParagraphStyle('Total', fontSize=9)
            ))
        else:
            story.append(Paragraph("Aucun étudiant affecté", styles['Normal']))

        if idx < len(repartitions) - 1:
            story.append(PageBreak())

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response


# ─────────────────────────────────────────────────────────────────
# CONVOCATIONS — vue liste
# ─────────────────────────────────────────────────────────────────
@staff_member_required
def convocations_view(request):
    sessions         = Session.objects.filter(is_active=True).order_by('-date_debut')
    selected_session = None
    session_id       = request.GET.get('session')

    if session_id:
        selected_session = get_object_or_404(Session, id=session_id)
        surveillants = Surveillant.objects.filter(
            repartition__examen__session=selected_session
        ).distinct().annotate(examens_count=Count('repartition__examen', distinct=True))
    else:
        surveillants = Surveillant.objects.annotate(
            examens_count=Count('repartition__examen', distinct=True)
        ).filter(examens_count__gt=0)

    context = {
        **admin.site.each_context(request),
        'sessions':         sessions,
        'selected_session': selected_session,
        'session_id':       session_id,
        'surveillants':     surveillants,
        'title':            'Convocations des Surveillants',
    }
    return render(request, 'admin/examens/convocations.html', context)


# ─────────────────────────────────────────────────────────────────
# CONVOCATION PDF — helper interne
# ─────────────────────────────────────────────────────────────────
def _get_convocation_pdf_bytes(surveillant, session_id=None):
    """Génère et retourne les bytes bruts du PDF de convocation."""
    repartitions = Repartition.objects.filter(surveillants=surveillant)
    session_name = None
    if session_id:
        repartitions = repartitions.filter(examen__session_id=session_id)
        session      = get_object_or_404(Session, pk=session_id)
        session_name = session.nom
    else:
        latest = repartitions.order_by('examen__session__date_debut').first()
        if latest:
            session_name = latest.examen.session.nom

    repartitions = repartitions.order_by('examen__date', 'examen__heure_debut')

    buffer = BytesIO()
    doc    = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=2*cm, bottomMargin=2*cm,
        leftMargin=2*cm, rightMargin=2*cm
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'TitleStyle', parent=styles['Heading1'],
        fontSize=16, alignment=TA_CENTER, spaceAfter=5,
        textColor=colors.HexColor("#081B35"), fontName='Helvetica-Bold'
    )
    subtitle_style = ParagraphStyle(
        'SubtitleStyle', parent=styles['Heading1'],
        fontSize=16, alignment=TA_CENTER, spaceAfter=10,
        textColor=colors.HexColor("#081B35"), fontName='Helvetica-Bold'
    )
    attention_style = ParagraphStyle(
        'AttentionStyle', parent=styles['Normal'],
        fontSize=11, alignment=TA_CENTER, spaceAfter=15, fontName='Helvetica-Bold'
    )
    body_style = ParagraphStyle(
        'BodyStyle', parent=styles['Normal'],
        fontSize=10, alignment=TA_JUSTIFY, spaceAfter=15, leading=14
    )

    story = []

    logo_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'logo.png')
    if os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=8*cm, height=2*cm)
            logo.hAlign = 'CENTER'
            story.append(logo)
            story.append(Spacer(1, 20))
        except Exception:
            pass

    story.append(Paragraph("CONVOCATION À LA SURVEILLANCE DES EXAMENS", title_style))
    story.append(Paragraph(
        f"SESSION {session_name.upper()}" if session_name else "SESSION EN COURS",
        subtitle_style
    ))
    story.append(Spacer(1, 10))
    story.append(Paragraph(
        f"<b>A l'attention de :</b> {surveillant.specialite.upper()} {surveillant.nom.upper()}",
        attention_style
    ))
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        "La doyenne de la Faculté de Médecine de Pharmacie Laâyoune, vous informe que vous avez été "
        "désigné(e) pour assurer la surveillance lors des prochains examens qui auront lieu dans notre faculté.",
        body_style
    ))
    story.append(Paragraph("<b>Vous trouverez ci-dessous les détails de la surveillance :</b>", body_style))
    story.append(Spacer(1, 10))

    if repartitions.exists():
        table_data = [["Date et heure d'examen", "Matière", "Amphi / Salle"]]
        for rep in repartitions:
            exam = rep.examen
            date_time = (
                f"{exam.date.strftime('%d/%m/%Y')} – "
                f"{exam.heure_debut.strftime('%H:%M')} – "
                f"{exam.heure_fin.strftime('%H:%M')}"
            )
            table_data.append([date_time, exam.module, rep.amphi.nom])

        exam_table = Table(table_data, colWidths=[4.5*cm, 6.5*cm, 4*cm], repeatRows=1)
        exam_table.setStyle(TableStyle([
            ('BACKGROUND',    (0, 0), (-1, 0),  colors.HexColor("#10327c")),
            ('TEXTCOLOR',     (0, 0), (-1, 0),  colors.white),
            ('ALIGN',         (0, 0), (-1, 0),  'CENTER'),
            ('FONTNAME',      (0, 0), (-1, 0),  'Helvetica-Bold'),
            ('FONTSIZE',      (0, 0), (-1, 0),  9),
            ('BOTTOMPADDING', (0, 0), (-1, 0),  8),
            ('TOPPADDING',    (0, 0), (-1, 0),  8),
            ('FONTSIZE',      (0, 1), (-1, -1), 8),
            ('ALIGN',         (0, 1), (0,  -1), 'CENTER'),
            ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID',          (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            ('TOPPADDING',    (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('LEFTPADDING',   (0, 0), (-1, -1), 5),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 5),
        ]))
        story.append(exam_table)
        story.append(Spacer(1, 15))

    story.append(Paragraph(
        "<i>Si pour une raison de force majeure vous vous trouviez dans l'impossibilité d'assurer cette mission, "
        "il vous appartiendrait d'en aviser immédiatement par téléphone l'administration de la faculté.</i>",
        body_style
    ))
    story.append(Spacer(1, 15))
    story.append(Paragraph("<b>Nous tenons à vous remercier d'avance pour votre collaboration.</b>", body_style))
    story.append(Spacer(1, 25))

    cache_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'Cache.png')
    if os.path.exists(cache_path):
        try:
            cache = Image(cache_path, width=6*cm, height=4.5*cm)
            cache.hAlign = 'CENTER'
            story.append(cache)
            story.append(Spacer(1, 10))
        except Exception:
            pass

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes


# ─────────────────────────────────────────────────────────────────
# CONVOCATION PDF — vue individuelle
# ─────────────────────────────────────────────────────────────────
@staff_member_required
def generate_convocation_pdf(request, surveillant_id, session_id=None):
    surveillant = get_object_or_404(Surveillant, pk=surveillant_id)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="convocation_{surveillant.nom}.pdf"'

    pdf_bytes = _get_convocation_pdf_bytes(surveillant, session_id)
    response.write(pdf_bytes)
    return response


# ─────────────────────────────────────────────────────────────────
# CONVOCATIONS BULK — ZIP
# ─────────────────────────────────────────────────────────────────
@staff_member_required
def convocation_bulk_pdf(request):
    import zipfile

    surveillant_ids = request.GET.get('ids', '')
    session_id      = request.GET.get('session')

    if surveillant_ids:
        surveillant_ids = [i for i in surveillant_ids.split(',') if i and i.strip()]
    else:
        surveillant_ids = []

    valid_ids = []
    for id_str in surveillant_ids:
        try:
            valid_ids.append(int(id_str))
        except ValueError:
            continue

    if not valid_ids:
        from django.contrib import messages
        messages.error(request, "Aucun surveillant sélectionné.")
        return redirect('examens:convocations')

    surveillants = Surveillant.objects.filter(id__in=valid_ids)

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for surveillant in surveillants:
            sid = None
            if session_id and session_id not in ('', 'None'):
                try:
                    sid = int(session_id)
                except ValueError:
                    pass
            pdf_bytes = _get_convocation_pdf_bytes(surveillant, sid)
            zip_file.writestr(f"convocation_{surveillant.nom}.pdf", pdf_bytes)

    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="convocations_surveillants.zip"'
    return response


# ─────────────────────────────────────────────────────────────────
# ENVOI EMAIL
# ─────────────────────────────────────────────────────────────────
@staff_member_required
def send_convocation_email(request, surveillant_id, session_id=None):
    from django.contrib import messages

    surveillant = get_object_or_404(Surveillant, pk=surveillant_id)

    if not surveillant.email:
        messages.error(request, f"❌ {surveillant.nom} n'a pas d'adresse email.")
        return redirect('examens:convocations')

    try:
        pdf_bytes = _get_convocation_pdf_bytes(surveillant, session_id)
        mail = EmailMessage(
            subject='Convocation à la surveillance des examens — FMPL Laâyoune',
            body=(
                f"Madame/Monsieur {surveillant.nom},\n\n"
                "Veuillez trouver ci-joint votre convocation pour la surveillance des examens.\n\n"
                "Cordialement,\nAdministration FMPL Laâyoune"
            ),
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            to=[surveillant.email],
        )
        mail.attach(f'convocation_{surveillant.nom}.pdf', pdf_bytes, 'application/pdf')
        mail.send()
        messages.success(request, f"✅ Email envoyé à {surveillant.nom} ({surveillant.email})")
    except Exception as e:
        messages.error(request, f"❌ Erreur envoi email : {str(e)}")

    return redirect('examens:convocations')


# ─────────────────────────────────────────────────────────────────
# ENVOI WHATSAPP
# ─────────────────────────────────────────────────────────────────
@staff_member_required
def send_convocation_whatsapp(request, surveillant_id, session_id=None):
    from django.contrib import messages
    from twilio.rest import Client

    surveillant = get_object_or_404(Surveillant, pk=surveillant_id)

    if not surveillant.telephone:
        messages.error(request, f"❌ {surveillant.nom} n'a pas de numéro de téléphone.")
        return redirect('examens:convocations')

    try:
        phone = surveillant.telephone.strip().replace(' ', '')
        if phone.startswith('0'):
            phone = '+212' + phone[1:]
        elif not phone.startswith('+'):
            phone = '+212' + phone

        repartitions = Repartition.objects.filter(surveillants=surveillant)
        if session_id:
            repartitions = repartitions.filter(examen__session_id=session_id)
        repartitions = repartitions.order_by('examen__date', 'examen__heure_debut')

        lines = ['📋 *Convocation FMPL Laâyoune*\n',
                 f'Madame/Monsieur *{surveillant.nom}*,\n',
                 'Vous êtes convoqué(e) pour surveiller les examens suivants :\n']
        for rep in repartitions:
            e = rep.examen
            lines.append(
                f'📅 {e.date.strftime("%d/%m/%Y")} | '
                f'🕐 {e.heure_debut.strftime("%H:%M")}–{e.heure_fin.strftime("%H:%M")} | '
                f'📚 {e.module} | 🏛 {rep.amphi.nom}'
            )
        lines.append('\nMerci pour votre collaboration.\n_Administration FMPL Laâyoune_')

        client = Client(django_settings.TWILIO_ACCOUNT_SID, django_settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            from_=django_settings.TWILIO_WHATSAPP_FROM,
            to=f'whatsapp:{phone}',
            body='\n'.join(lines),
        )
        messages.success(request, f"✅ WhatsApp envoyé à {surveillant.nom} ({phone})")
    except Exception as e:
        messages.error(request, f"❌ Erreur WhatsApp : {str(e)}")

    return redirect('examens:convocations')


# ─────────────────────────────────────────────────────────────────
# ENVOI BULK (email + whatsapp)
# ─────────────────────────────────────────────────────────────────
@staff_member_required
def send_bulk_notifications(request):
    from django.contrib import messages

    ids        = request.GET.get('ids', '').split(',')
    session_id = request.GET.get('session')
    channel    = request.GET.get('channel', 'email')

    sent, failed = 0, 0
    for sid in ids:
        if not sid.strip():
            continue
        try:
            surveillant = Surveillant.objects.get(pk=int(sid))
            if channel == 'whatsapp':
                _send_whatsapp(surveillant, session_id)
            else:
                _send_email(surveillant, session_id)
            sent += 1
        except Exception:
            failed += 1

    messages.success(
        request,
        f" {sent} envoi(s) réussi(s){f', {failed} échec(s)' if failed else ''}."
    )
    return redirect('examens:convocations')


# ─────────────────────────────────────────────────────────────────
# PROCÈS VERBAL
# ─────────────────────────────────────────────────────────────────
@staff_member_required
def generate_proces_verbal(request, repartition_id):
    from .pdf_generator import ProcesVerbalPDF

    repartition = get_object_or_404(Repartition, id=repartition_id)
    response    = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="proces_verbal_{repartition.id}.pdf"'

    pdf_generator = ProcesVerbalPDF(repartition)
    return pdf_generator.generate(response)


# ─────────────────────────────────────────────────────────────────
# DASHBOARD STATS
# ─────────────────────────────────────────────────────────────────
@staff_member_required
def dashboard_stats(request):
    from etudiants.models import Etudiant
    from salles.models import Amphi
    from portal.models import Presence
    from django.contrib.admin.models import LogEntry

    log_entries = []
    for entry in LogEntry.objects.select_related('content_type', 'user').order_by('-action_time')[:10]:
        log_entries.append({
            'object_repr': entry.object_repr,
            'app':         entry.content_type.app_label,
            'model':       entry.content_type.model,
            'action':      ('Ajout' if entry.is_addition()
                            else 'Modification' if entry.is_change()
                            else 'Suppression'),
            'action_type': ('add' if entry.is_addition()
                            else 'change' if entry.is_change()
                            else 'delete'),
            'user':        entry.user.username,
            'time':        entry.action_time.strftime('%d/%m/%Y %H:%M'),
            'url':         (f'/admin/{entry.content_type.app_label}/'
                            f'{entry.content_type.model}/{entry.object_id}/change/'),
        })

    return JsonResponse({
        'etudiants':    Etudiant.objects.count(),
        'examens':      Examen.objects.count(),
        'surveillants': Surveillant.objects.count(),
        'repartitions': Repartition.objects.count(),
        'presences':    Presence.objects.count(),
        'salles':       Amphi.objects.count(),
        'log_entries':  log_entries,
    })


# ─────────────────────────────────────────────────────────────────
# SCAN QR SIÈGE (portal surveillant)
# ─────────────────────────────────────────────────────────────────
from datetime import date as _date
import json as _json

def scan_siege(request):
    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée."}, status=405)

    try:
        data         = _json.loads(request.body)
        siege_number = int(data["siege_number"])
    except (KeyError, ValueError, _json.JSONDecodeError):
        return JsonResponse({"error": "Données invalides."}, status=400)

    from examens.models import Repartitionsiege
    from portal.models import Presence

    surveillant = request.user.profile.surveillant

    assignment = Repartitionsiege.objects.filter(
        siege__siege_number=siege_number,
        repartition__examen__date=_date.today(),
        repartition__surveillants=surveillant,
    ).select_related("etudiant", "repartition", "siege__amphi").first()

    if not assignment:
        return JsonResponse(
            {"error": f"Aucun étudiant assigné au siège {siege_number} pour aujourd'hui."},
            status=404
        )

    presence, _ = Presence.objects.update_or_create(
        repartition=assignment.repartition,
        etudiant=assignment.etudiant,
        defaults={"present": True, "scanne_par": surveillant},
    )

    return JsonResponse({
        "ok":          True,
        "nom":         str(assignment.etudiant),
        "etudiant_id": assignment.etudiant.pk,
        "rep_id":      assignment.repartition.pk,
        "siege":       siege_number,
    })