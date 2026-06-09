# examens/pdf_generator.py - FINAL VERSION (FIXED)
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, gray, black, white
from reportlab.pdfgen import canvas
from datetime import datetime
import os


# ── Logo resolver ─────────────────────────────────────────────────────────────
def _resolve_logo():
    try:
        from django.conf import settings
        candidates = []
        for d in getattr(settings, "STATICFILES_DIRS", []):
            candidates.append(os.path.join(str(d), "images", "logo.png"))
        static_root = getattr(settings, "STATIC_ROOT", None)
        if static_root:
            candidates.append(os.path.join(str(static_root), "images", "logo.png"))
        base_dir = getattr(settings, "BASE_DIR", None)
        if base_dir:
            candidates.append(os.path.join(str(base_dir), "static", "images", "logo.png"))
        for c in candidates:
            if os.path.exists(c):
                return c
    except Exception:
        pass
    return None


# ── Color palette ──────────────────────────────────────────────────────────────
class C:
    NAVY        = HexColor('#1a3a5c')
    NAVY_DARK   = HexColor('#122840')
    GOLD        = HexColor('#c9a84c')
    RED         = HexColor('#b03a2e')
    BG_LIGHT    = HexColor('#f4f6f9')
    BG_MED      = HexColor("#ffffff")
    BORDER      = HexColor('#8fa3bb')
    BORDER_LITE = HexColor('#cdd8e3')
    TXT_DARK    = HexColor('#1c2833')
    TXT_MED     = HexColor('#4a607a')
    TXT_LIGHT   = HexColor('#7f8fa4')
    WHITE       = white


# ── Shared helpers ─────────────────────────────────────────────────────────────
def draw_logo_header(pdf, width, y_top, logo_path, logo_w=180, logo_h=60):
    if logo_path and os.path.exists(logo_path):
        pdf.drawImage(
            logo_path,
            (width - logo_w) / 2,
            y_top - logo_h,
            width=logo_w, height=logo_h,
            preserveAspectRatio=True, mask="auto",
        )
        return y_top - logo_h - 20
    return y_top - 25


def draw_double_bordered_box(pdf, x, y, w, h, line_width=0.8,
                      fill_color=None, border_color=None):
    """Draw a box with double border (outer and inner)"""
    stroke_color = border_color if border_color else C.BORDER
    
    # Outer border
    pdf.setStrokeColor(stroke_color)
    pdf.setLineWidth(line_width + 0.3)
    pdf.rect(x, y, w, h, stroke=1, fill=0)
    
    # Inner border (5 points inside)
    pdf.setLineWidth(line_width)
    pdf.rect(x + 3, y + 3, w - 6, h - 6, stroke=1, fill=0)
    
    # Fill if needed
    if fill_color:
        pdf.setFillColor(fill_color)
        pdf.rect(x + 3, y + 3, w - 6, h - 6, stroke=0, fill=1)
    
    pdf.setFillColor(C.TXT_DARK)


def draw_table_with_borders(pdf, x, y_top, col_widths, rows,
                             header_row=True, row_height=30, alternate_rows=True,
                             is_surveillant_table=False, merge_module=False, module_text=""):
    """
    Draw a table with borders - for surveillant table, only vertical borders (no horizontal)
    merge_module: If True, merge first column and center the module text
    module_text: Text to display in the merged cell
    """
    total_width = sum(col_widths)
    n_rows = len(rows)
    y_bottom = y_top - n_rows * row_height

    # Header background
    if header_row and rows:
        pdf.setFillColor(C.NAVY)
        pdf.rect(x, y_top - row_height, total_width, row_height, stroke=0, fill=1)

    # Alternating row backgrounds
    if alternate_rows and not is_surveillant_table:
        for r_idx in range(1 if header_row else 0, n_rows):
            if r_idx % 2 == 1:
                pdf.setFillColor(C.BG_MED)
                pdf.rect(x, y_top - (r_idx + 1) * row_height,
                         total_width, row_height, stroke=0, fill=1)

    # Draw borders
    if is_surveillant_table:
        # Only vertical borders for surveillant table
        pdf.setStrokeColor(C.BORDER)
        pdf.setLineWidth(0.9)
        pdf.line(x, y_top, x, y_bottom)  # Left border
        pdf.line(x + total_width, y_top, x + total_width, y_bottom)  # Right border
        
        # Inner vertical lines
        pdf.setLineWidth(0.4)
        pdf.setStrokeColor(C.BORDER_LITE)
        x_pos = x
        for w in col_widths[:-1]:
            x_pos += w
            pdf.line(x_pos, y_top, x_pos, y_bottom)
            
        # Draw top and bottom header borders only
        pdf.setStrokeColor(C.BORDER)
        pdf.setLineWidth(0.9)
        pdf.line(x, y_top, x + total_width, y_top)  # Top border of header
        pdf.line(x, y_top - row_height, x + total_width, y_top - row_height)  # Bottom border of header
        pdf.line(x, y_bottom, x + total_width, y_bottom)  # Bottom border of table
    else:
        # Normal table borders
        pdf.setStrokeColor(C.BORDER)
        pdf.setLineWidth(0.9)
        pdf.rect(x, y_bottom, total_width, n_rows * row_height, stroke=1, fill=0)

        # Inner horizontal lines
        pdf.setLineWidth(0.4)
        pdf.setStrokeColor(C.BORDER_LITE)
        for i in range(1, n_rows):
            yl = y_top - i * row_height
            pdf.line(x, yl, x + total_width, yl)

        # Inner vertical lines
        x_pos = x
        for w in col_widths[:-1]:
            x_pos += w
            pdf.line(x_pos, y_top, x_pos, y_bottom)

    # Draw merged module cell if needed (for surveillant table)
    if merge_module and is_surveillant_table and module_text:
        data_rows = n_rows - 1
        if data_rows > 0:
            total_merged_height = data_rows * row_height
            center_y = y_top - row_height - (total_merged_height / 2)
            pdf.setFont("Helvetica-Bold", 11)
            pdf.setFillColor(C.TXT_DARK)
            pdf.drawCentredString(x + col_widths[0] / 2, center_y - 3, module_text.upper())

    # Cell text
    for r_idx, row in enumerate(rows):
        is_header = header_row and r_idx == 0
        font_name = "Helvetica-Bold" if is_header else "Helvetica"
        font_size = 9 if is_header else 8
        pdf.setFont(font_name, font_size)

        x_pos = x
        for c_idx, cell_text in enumerate(row):
            if c_idx >= len(col_widths):
                continue
            cell_w = col_widths[c_idx]
            
            # Skip drawing text in first column if we're merging it
            if merge_module and is_surveillant_table and c_idx == 0 and not is_header:
                x_pos += cell_w
                continue
                
            text = str(cell_text).upper() if cell_text else ""

            if '\n' in text:
                lines = text.split('\n')
            else:
                lines_out, cur = [], ""
                for word in text.split():
                    test = (cur + " " + word).strip()
                    if pdf.stringWidth(test, font_name, font_size) < cell_w - 12:
                        cur = test
                    else:
                        if cur: lines_out.append(cur)
                        cur = word
                if cur: lines_out.append(cur)
                lines = lines_out if lines_out else [text]

            total_text_h = len(lines) * (font_size + 2)
            start_y = (y_top - r_idx * row_height
                       - (row_height - total_text_h) / 2 - (font_size - 2))

            pdf.setFillColor(C.WHITE if is_header else C.TXT_DARK)

            for li, ln in enumerate(lines):
                ty = start_y - li * (font_size + 2)
                if c_idx == 0:
                    pdf.drawString(x_pos + 6, ty, ln)
                else:
                    pdf.drawCentredString(x_pos + cell_w / 2, ty, ln)

            x_pos += cell_w

    return y_bottom - 8


# ── Main class ─────────────────────────────────────────────────────────────────
class ProcesVerbalPDF:
    def __init__(self, repartition, logo_path=None):
        self.repartition  = repartition
        self.examen       = repartition.examen
        self.amphi        = repartition.amphi
        self.session      = self.examen.session
        self.students     = repartition.etudiants.all()
        self.surveillants = repartition.surveillants.all()
        self._logo = logo_path if (logo_path and os.path.exists(logo_path)) \
                     else _resolve_logo()

    def generate(self, response):
        pdf = canvas.Canvas(response, pagesize=A4)
        width, height = A4
        self.draw_page_one(pdf, width, height)
        pdf.showPage()
        self.draw_page_two(pdf, width, height)
        pdf.showPage()
        self.draw_page_three(pdf, width, height)
        pdf.save()
        return response

    def _session_label(self):
        return "NORMALE" if self.session.type == "normal" else "RATTRAPAGE"

    def _semester_label(self):
        semester_map = {
            '1': 'SEMESTRE 1', '2': 'SEMESTRE 2', '3': 'SEMESTRE 3',
            '4': 'SEMESTRE 4', '5': 'SEMESTRE 5', '6': 'SEMESTRE 6',
            '7': 'SEMESTRE 7', '8': 'SEMESTRE 8', '9': 'SEMESTRE 9',
            '10': 'SEMESTRE 10', '11': 'SEMESTRE 11', '12': 'SEMESTRE 12'
        }
        return semester_map.get(self.examen.semester, f"SEMESTRE {self.examen.semester}")

    def _stats(self):
        total = self.students.count()
        absents = 0
        participants = total - absents
        h = self.examen.heure_fin.hour - self.examen.heure_debut.hour
        m = self.examen.heure_fin.minute - self.examen.heure_debut.minute
        if m < 0:
            h -= 1
            m += 60
        duration = f"{h}H" if m == 0 else f"{h}H{m:02d}"
        return total, participants, absents, duration

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 1 — Cover
    # ═══════════════════════════════════════════════════════════════════════════
    def draw_page_one(self, pdf, width, height):
        margin = 60
        y = height - 40

        y = draw_logo_header(pdf, width, y, self._logo, logo_w=200, logo_h=70)

        pdf.setFillColor(C.NAVY)
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawCentredString(width / 2, y, "FACULTE DE MEDECINE ET DE PHARMACIE LAAYOUNE")
        y -= 24
        pdf.setFillColor(C.TXT_MED)
        pdf.setFont("Helvetica", 11)
        pdf.drawCentredString(width / 2, y, f"ANNEE UNIVERSITAIRE {self.examen.annee.annee_universitaire}")
        y -= 55

        box_h = 110
        draw_double_bordered_box(pdf, margin, y - box_h, width - 2 * margin, box_h,
                        line_width=1.2, fill_color=C.BG_LIGHT, border_color=C.NAVY)
        pdf.setFillColor(C.NAVY)
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawCentredString(width / 2, y - 31, "PROCES VERBAL DES EPREUVES ECRITES")
        pdf.setFillColor(C.TXT_MED)
        pdf.setFont("Helvetica", 11)
        pdf.drawCentredString(width / 2, y - 55, f"EVALUATIONS DU {self._semester_label()} - SESSION {self._session_label()}")
        exam_date = self.examen.date.strftime("%d %B %Y").upper()
        pdf.setFillColor(C.NAVY)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawCentredString(width / 2, y - 80, exam_date)
        y -= box_h + 50

        salle_box_h = 45
        draw_double_bordered_box(pdf, margin + 30, y - salle_box_h,
                        width - 2 * (margin + 30), salle_box_h,
                        line_width=0.8, border_color=C.NAVY)
        pdf.setFillColor(C.NAVY)
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawCentredString(width / 2, y - 25, f"SALLE :  {self.amphi.nom}")
        y -= salle_box_h + 40

        mod_box_h = 85
        draw_double_bordered_box(pdf, margin, y - mod_box_h, width - 2 * margin, mod_box_h,
                        line_width=0.8, fill_color=C.BG_LIGHT, border_color=C.BORDER)
        
        pdf.setFillColor(C.TXT_MED)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawCentredString(width / 2, y - 28, "MODULE :")
        
        pdf.setFillColor(C.TXT_DARK)
        pdf.setFont("Helvetica", 11)
        
        module_text = self.examen.module.upper()
        max_chars_per_line = 60
        
        if len(module_text) > max_chars_per_line:
            words = module_text.split()
            lines = []
            current_line = ""
            for word in words:
                if len(current_line) + len(word) + 1 <= max_chars_per_line:
                    if current_line:
                        current_line += " " + word
                    else:
                        current_line = word
                else:
                    lines.append(current_line)
                    current_line = word
            if current_line:
                lines.append(current_line)
            
            line_height = 18
            start_y = y - 48 - ((len(lines) - 1) * (line_height - 5))
            for i, line in enumerate(lines):
                pdf.drawCentredString(width / 2, start_y - (i * line_height), line)
        else:
            pdf.drawCentredString(width / 2, y - 48, module_text)
        
        y -= mod_box_h + 50

        pdf.setStrokeColor(C.GOLD)
        pdf.setLineWidth(1.0)
        pdf.line(margin, y - 20, width - margin, y - 20)
        pdf.setFillColor(C.TXT_LIGHT)
        pdf.setFont("Helvetica", 12)
        pdf.drawCentredString(width / 2, y - 35, f"{self.examen.annee.annee_universitaire}")

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 2 — Décharge
    # ═══════════════════════════════════════════════════════════════════════════
    def draw_page_two(self, pdf, width, height):
        margin = 55
        y = height - 45

        y = draw_logo_header(pdf, width, y, self._logo)
        y -= 0
        
        b1_h = 32
        draw_double_bordered_box(pdf, margin, y - b1_h, width - 2 * margin, b1_h,
                          fill_color=C.NAVY, line_width=0.8, border_color=C.NAVY)
        pdf.setFillColor(C.WHITE)
        pdf.setFont("Helvetica-Bold", 19)
        pdf.drawCentredString(width / 2, y - 20, "DECHARGE")
        y -= b1_h + 8

        box_h = 55
        draw_double_bordered_box(pdf, margin, y - box_h, width - 2 * margin, box_h,
                          fill_color=C.BG_LIGHT, line_width=0.8, border_color=C.BORDER)
        pdf.setFillColor(C.NAVY)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawCentredString(width / 2, y - 20, f"EXAMEN DES {self._semester_label()} - SESSION {self._session_label()}")
        exam_date = self.examen.date.strftime("%B %Y").upper()
        pdf.setFillColor(C.TXT_MED)
        pdf.setFont("Helvetica", 10)
        pdf.drawCentredString(width / 2, y - 38, f"SESSION {exam_date}")
        y -= box_h + 28

        # Module line
        pdf.setFillColor(C.NAVY)
        pdf.setFont("Helvetica-Bold", 11)
        mod_label = "MODULE : "
        pdf.drawString(margin, y, mod_label)
        
        pdf.setFillColor(C.TXT_DARK)
        pdf.setFont("Helvetica", 11)
        module_text = self.examen.module.upper()
        pdf.drawString(margin + 80, y, module_text)
        
        module_text_width = pdf.stringWidth(module_text, "Helvetica", 11)
        pdf.setStrokeColor(C.BORDER_LITE)
        pdf.setLineWidth(0.8)
        pdf.line(margin + 80, y - 3, margin + 80 + module_text_width, y - 3)
        y -= 25

        # Salle line
        pdf.setFillColor(C.NAVY)
        pdf.setFont("Helvetica-Bold", 11)
        salle_label = "SALLE : "
        pdf.drawString(margin, y, salle_label)
        
        pdf.setFillColor(C.TXT_DARK)
        pdf.setFont("Helvetica", 11)
        salle_text = self.amphi.nom.upper()
        pdf.drawString(margin + 70, y, salle_text)
        
        salle_text_width = pdf.stringWidth(salle_text, "Helvetica", 11)
        pdf.setStrokeColor(C.BORDER_LITE)
        pdf.setLineWidth(0.8)
        pdf.line(margin + 70, y - 3, margin + 70 + salle_text_width, y - 3)
        y -= 30

        # Stats table
        total, participants, absents, duration = self._stats()
        y = draw_table_with_borders(pdf, margin, y,
            [135, 95, 90, 80, 100],
            [["EPREUVE", "INSCRITS", "PARTICIPANTS", "ABSENTS", "DUREE"],
             [self.examen.module.upper(), str(total), str(participants), str(absents), duration]],
            row_height=38)
        y -= 28

        # Surveillants table - WITH merged module cell
        y = draw_table_with_borders(pdf, margin, y,
            [135, 155, 105, 107],
            [["MATIERE", "NOMS ET PRENOMS DES SURVEILLANTS", "SIGNATURES", "OBSERVATIONS"],
             ["", "", "", ""],
             ["", "", "", ""],
             ["", "", "", ""]],
            row_height=42,
            is_surveillant_table=True,
            merge_module=True,
            module_text=self.examen.module.upper())

        # Footer
        today = datetime.now().strftime("%d/%m/%Y")
        pdf.setFillColor(C.TXT_MED)
        pdf.setFont("Helvetica", 9)
        pdf.drawRightString(width - margin, 60, f"LAAYOUNE, LE {today}")

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 3 — Full Procès Verbal
    # ═══════════════════════════════════════════════════════════════════════════
    def draw_page_three(self, pdf, width, height):
        margin = 55
        y = height - 45

        y = draw_logo_header(pdf, width, y, self._logo)

        pdf.setFillColor(C.NAVY)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawCentredString(width / 2, y, "FACULTE DE MEDECINE ET DE PHARMACIE LAAYOUNE")
        y -= 20
        pdf.setFillColor(C.TXT_MED)
        pdf.setFont("Helvetica", 10)
        pdf.drawCentredString(width / 2, y, f"ANNEE UNIVERSITAIRE {self.examen.annee.annee_universitaire}")
        y -= 35

        b1_h = 32
        draw_double_bordered_box(pdf, margin, y - b1_h, width - 2 * margin, b1_h,
                          fill_color=C.NAVY, line_width=0.8, border_color=C.NAVY)
        pdf.setFillColor(C.WHITE)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawCentredString(width / 2, y - 20, "PROCES VERBAL DES EPREUVES ECRITES")
        y -= b1_h + 8

        b2_h = 48
        draw_double_bordered_box(pdf, margin, y - b2_h, width - 2 * margin, b2_h,
                          fill_color=C.BG_LIGHT, line_width=0.8, border_color=C.BORDER)
        pdf.setFillColor(C.NAVY)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawCentredString(width / 2, y - 16, f"EXAMEN DES {self._semester_label()} - SESSION {self._session_label()}")
        exam_date = self.examen.date.strftime("%B %Y").upper()
        pdf.setFillColor(C.TXT_MED)
        pdf.setFont("Helvetica", 10)
        pdf.drawCentredString(width / 2, y - 32, exam_date)
        y -= b2_h + 20

        pdf.setFillColor(C.NAVY)
        pdf.setFont("Helvetica-Bold", 11)
        mod_label = "MODULE : "
        mod_w = pdf.stringWidth(mod_label, "Helvetica-Bold", 11)
        pdf.drawString(margin, y, mod_label)
        pdf.setStrokeColor(C.BORDER_LITE)
        pdf.setLineWidth(0.8)
        pdf.line(margin, y - 3, margin + mod_w + 250, y - 3)
        pdf.setFillColor(C.TXT_DARK)
        pdf.setFont("Helvetica", 11)
        pdf.drawString(margin + mod_w + 5, y, self.examen.module.upper())
        y -= 28

        pdf.setFillColor(C.NAVY)
        pdf.setFont("Helvetica-Bold", 11)
        salle_label = "SALLE : "
        salle_w = pdf.stringWidth(salle_label, "Helvetica-Bold", 11)
        pdf.drawString(margin, y, salle_label)
        pdf.setStrokeColor(C.BORDER_LITE)
        pdf.line(margin, y - 3, margin + salle_w + 250, y - 3)
        pdf.setFillColor(C.TXT_DARK)
        pdf.setFont("Helvetica", 11)
        pdf.drawString(margin + salle_w + 5, y, self.amphi.nom.upper())
        y -= 35

        total, participants, absents, duration = self._stats()
        y = draw_table_with_borders(pdf, margin, y,
            [135, 95, 90, 80, 100],
            [["EPREUVE", "INSCRITS", "PARTICIPANTS", "ABSENTS", "DUREE"],
             [self.examen.module.upper(), str(total), str(participants), str(absents), duration]],
            row_height=38)
        y -= 25

        # Surveillants table - WITH merged module cell
        y = draw_table_with_borders(pdf, margin, y,
            [135, 155, 105, 107],
            [["MATIERE", "NOMS ET PRENOMS DES SURVEILLANTS", "SIGNATURES", "OBSERVATIONS"],
             ["", "", "", ""],
             ["", "", "", ""],
             ["", "", "", ""]],
            row_height=42,
            is_surveillant_table=True,
            merge_module=True,
            module_text=self.examen.module.upper())

        # Footer
        today = datetime.now().strftime("%d/%m/%Y")
        pdf.setFillColor(C.TXT_MED)
        pdf.setFont("Helvetica", 9)
        pdf.drawRightString(width - margin, 60, f"LAAYOUNE, LE {today}")