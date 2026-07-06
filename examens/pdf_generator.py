# examens/pdf_generator.py - FINAL VERSION (FIXED)
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, gray, black, white
from reportlab.pdfgen import canvas
from datetime import datetime
import os

# ── Mois en français ───────────────────────────────────────────────────────────
MOIS_FR = {
    1: "janvier",  2: "février",  3: "mars",     4: "avril",
    5: "mai",      6: "juin",     7: "juillet",  8: "août",
    9: "septembre",10: "octobre", 11: "novembre",12: "décembre"
}

def date_fr(d, fmt="full"):
    """
    fmt='full'  → '11 juin 2026'
    fmt='month' → 'juin 2026'
    """
    if fmt == "month":
        return f"{MOIS_FR[d.month]} {d.year}"
    return f"{d.day:02d} {MOIS_FR[d.month]} {d.year}"


# ── Logo resolver ──────────────────────────────────────────────────────────────
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


# ── Word-wrap helper ───────────────────────────────────────────────────────────
def _wrap_text(pdf, text, font_name, font_size, max_width):
    """Split text into lines that fit within max_width."""
    words = text.split()
    lines, cur = [], ""
    for word in words:
        test = (cur + " " + word).strip()
        if pdf.stringWidth(test, font_name, font_size) <= max_width:
            cur = test
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines if lines else [text]


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
    stroke_color = border_color if border_color else C.BORDER
    pdf.setStrokeColor(stroke_color)
    pdf.setLineWidth(line_width + 0.3)
    pdf.rect(x, y, w, h, stroke=1, fill=0)
    pdf.setLineWidth(line_width)
    pdf.rect(x + 3, y + 3, w - 6, h - 6, stroke=1, fill=0)
    if fill_color:
        pdf.setFillColor(fill_color)
        pdf.rect(x + 3, y + 3, w - 6, h - 6, stroke=0, fill=1)
    pdf.setFillColor(C.TXT_DARK)


def draw_table_with_borders(pdf, x, y_top, col_widths, rows,
                             header_row=True, row_height=30, alternate_rows=True,
                             is_surveillant_table=False, merge_module=False,
                             module_text=""):
    """
    Draw a bordered table.
    - For the surveillant table: only vertical borders between columns + outer frame.
    - merge_module: merges the first data column and centres module_text vertically.
    - Cells with long text auto-wrap; row height expands if needed.
    """
    total_width = sum(col_widths)
    n_rows = len(rows)

    # ── Pre-compute wrapped lines and actual row heights ──────────────────────
    cell_lines = []   # list of rows; each row is a list of line-lists per cell
    row_heights = []  # actual height for each row

    for r_idx, row in enumerate(rows):
        is_header = header_row and r_idx == 0
        font_name = "Helvetica-Bold" if is_header else "Helvetica"
        font_size = 9 if is_header else 8
        line_h    = font_size + 2

        row_line_lists = []
        max_lines = 1
        for c_idx, cell_text in enumerate(row):
            if c_idx >= len(col_widths):
                row_line_lists.append([""])
                continue
            # Skip first data column if merging module
            if merge_module and is_surveillant_table and c_idx == 0 and not is_header:
                row_line_lists.append([""])
                continue

            text = str(cell_text).upper() if cell_text else ""
            if '\n' in text:
                lines = text.split('\n')
            else:
                lines = _wrap_text(pdf, text, font_name, font_size,
                                   col_widths[c_idx] - 12)
            row_line_lists.append(lines)
            max_lines = max(max_lines, len(lines))

        cell_lines.append(row_line_lists)
        needed_h = max_lines * line_h + 14   # 7pt top+bottom padding
        row_heights.append(max(row_height, needed_h))

    total_height = sum(row_heights)
    y_bottom     = y_top - total_height

    # ── Header background ──────────────────────────────────────────────────────
    if header_row and rows:
        pdf.setFillColor(C.NAVY)
        pdf.rect(x, y_top - row_heights[0], total_width, row_heights[0],
                 stroke=0, fill=1)

    # ── Alternating backgrounds (non-surveillant tables) ──────────────────────
    if alternate_rows and not is_surveillant_table:
        cy = y_top - row_heights[0]
        for r_idx in range(1, n_rows):
            if r_idx % 2 == 1:
                pdf.setFillColor(C.BG_MED)
                pdf.rect(x, cy - row_heights[r_idx], total_width,
                         row_heights[r_idx], stroke=0, fill=1)
            cy -= row_heights[r_idx]

    # ── Border lines ───────────────────────────────────────────────────────────
    if is_surveillant_table:
        pdf.setStrokeColor(C.BORDER)
        pdf.setLineWidth(0.9)
        # Outer frame
        pdf.line(x, y_top,    x + total_width, y_top)
        pdf.line(x, y_bottom, x + total_width, y_bottom)
        pdf.line(x, y_top,    x, y_bottom)
        pdf.line(x + total_width, y_top, x + total_width, y_bottom)
        # Header bottom
        pdf.line(x, y_top - row_heights[0], x + total_width, y_top - row_heights[0])
        # Inner vertical lines
        pdf.setLineWidth(0.4)
        pdf.setStrokeColor(C.BORDER_LITE)
        xp = x
        for cw in col_widths[:-1]:
            xp += cw
            pdf.line(xp, y_top, xp, y_bottom)
    else:
        pdf.setStrokeColor(C.BORDER)
        pdf.setLineWidth(0.9)
        pdf.rect(x, y_bottom, total_width, total_height, stroke=1, fill=0)
        pdf.setLineWidth(0.4)
        pdf.setStrokeColor(C.BORDER_LITE)
        cy = y_top
        for r_idx in range(1, n_rows):
            cy -= row_heights[r_idx - 1]
            pdf.line(x, cy, x + total_width, cy)
        xp = x
        for cw in col_widths[:-1]:
            xp += cw
            pdf.line(xp, y_top, xp, y_bottom)

    # ── Merged module cell (surveillant table) ────────────────────────────────
    if merge_module and is_surveillant_table and module_text:
        data_height = sum(row_heights[1:])
        center_y    = y_top - row_heights[0] - data_height / 2
        # Word-wrap the module name within the first column width
        font_size   = 9
        font_name   = "Helvetica-Bold"
        lines       = _wrap_text(pdf, module_text.upper(), font_name, font_size,
                                 col_widths[0] - 12)
        line_h      = font_size + 3
        total_lh    = len(lines) * line_h
        start_y     = center_y + total_lh / 2 - font_size + 2
        pdf.setFont(font_name, font_size)
        pdf.setFillColor(C.TXT_DARK)
        for li, ln in enumerate(lines):
            pdf.drawCentredString(x + col_widths[0] / 2,
                                  start_y - li * line_h, ln)

    # ── Cell text ─────────────────────────────────────────────────────────────
    cy = y_top
    for r_idx, row in enumerate(rows):
        rh        = row_heights[r_idx]
        is_header = header_row and r_idx == 0
        font_name = "Helvetica-Bold" if is_header else "Helvetica"
        font_size = 9 if is_header else 8
        line_h    = font_size + 2
        pdf.setFont(font_name, font_size)

        xp = x
        for c_idx, cell_text in enumerate(row):
            if c_idx >= len(col_widths):
                xp += col_widths[c_idx] if c_idx < len(col_widths) else 0
                continue
            cw = col_widths[c_idx]

            # Skip first data col if merging
            if merge_module and is_surveillant_table and c_idx == 0 and not is_header:
                xp += cw
                continue

            lines    = cell_lines[r_idx][c_idx] if c_idx < len(cell_lines[r_idx]) else [""]
            total_lh = len(lines) * line_h
            start_y  = cy - (rh - total_lh) / 2 - font_size + 2

            pdf.setFillColor(C.WHITE if is_header else C.TXT_DARK)
            for li, ln in enumerate(lines):
                ty = start_y - li * line_h
                if c_idx == 0:
                    pdf.drawString(xp + 6, ty, ln)
                else:
                    pdf.drawCentredString(xp + cw / 2, ty, ln)

            xp += cw
        cy -= rh

    return y_bottom - 8


# ══════════════════════════════════════════════════════════════════════════════
class ProcesVerbalPDF:
    def __init__(self, repartition, logo_path=None):
        self.repartition  = repartition
        self.examen       = repartition.examen
        self.amphi        = repartition.amphi
        self.session      = self.examen.session
        self.students     = repartition.etudiants.all()
        self.surveillants = repartition.surveillants.all()
        self._logo = (logo_path if (logo_path and os.path.exists(logo_path))
                      else _resolve_logo())

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
        m = {
            '1':'SEMESTRE 1','2':'SEMESTRE 2','3':'SEMESTRE 3',
            '4':'SEMESTRE 4','5':'SEMESTRE 5','6':'SEMESTRE 6',
            '7':'SEMESTRE 7','8':'SEMESTRE 8','9':'SEMESTRE 9',
            '10':'SEMESTRE 10','11':'SEMESTRE 11','12':'SEMESTRE 12',
        }
        return m.get(self.examen.semester, f"SEMESTRE {self.examen.semester}")

    def _stats(self):
        total        = self.students.count()
        absents      = 0
        participants = total - absents
        h = self.examen.heure_fin.hour   - self.examen.heure_debut.hour
        mn = self.examen.heure_fin.minute - self.examen.heure_debut.minute
        if mn < 0:
            h -= 1; mn += 60
        duration = f"{h}H" if mn == 0 else f"{h}H{mn:02d}"
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
        pdf.drawCentredString(width / 2, y,
            "FACULTE DE MEDECINE ET DE PHARMACIE LAAYOUNE")
        y -= 24
        pdf.setFillColor(C.TXT_MED)
        pdf.setFont("Helvetica", 11)
        pdf.drawCentredString(width / 2, y,
            f"ANNEE UNIVERSITAIRE {self.examen.annee.annee_universitaire}- {self.examen.annee.filiere.upper()}")
        y -= 55

        # ── Grand encadré titre ──
        box_h = 110
        draw_double_bordered_box(pdf, margin, y - box_h, width - 2 * margin, box_h,
                                 line_width=1.2, fill_color=C.BG_LIGHT, border_color=C.NAVY)
        pdf.setFillColor(C.NAVY)
        pdf.setFont("Helvetica-Bold", 18)
        pdf.drawCentredString(width / 2, y - 31, "PROCES VERBAL DES EPREUVES ECRITES")
        pdf.setFillColor(C.TXT_MED)
        pdf.setFont("Helvetica", 11)
        pdf.drawCentredString(width / 2, y - 55,
            f"EVALUATIONS DU {self._semester_label()} - SESSION {self._session_label()}")

        # ← date_fr() ici
        pdf.setFillColor(C.NAVY)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawCentredString(width / 2, y - 80,
            date_fr(self.examen.date).upper())
        y -= box_h + 50

        # ── SALLE ──
        salle_box_h = 45
        draw_double_bordered_box(pdf, margin + 30, y - salle_box_h,
                                 width - 2 * (margin + 30), salle_box_h,
                                 line_width=0.8, border_color=C.NAVY)
        pdf.setFillColor(C.NAVY)
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawCentredString(width / 2, y - 25, f"SALLE :  {self.amphi.nom}")
        y -= salle_box_h + 40

        # ── MODULE (avec retour à la ligne) ──
        mod_box_h = 85
        draw_double_bordered_box(pdf, margin, y - mod_box_h, width - 2 * margin,
                                 mod_box_h, line_width=0.8, fill_color=C.BG_LIGHT,
                                 border_color=C.BORDER)

        pdf.setFillColor(C.TXT_MED)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawCentredString(width / 2, y - 28, "MODULE :")

        pdf.setFillColor(C.TXT_DARK)
        pdf.setFont("Helvetica", 11)
        module_text = self.examen.module.upper()
        lines = _wrap_text(pdf, module_text, "Helvetica", 11, width - 2 * margin - 30)
        line_h = 16
        total_lh = len(lines) * line_h
        start_y  = y - 48 - (total_lh - line_h) / 2
        for i, ln in enumerate(lines):
            pdf.drawCentredString(width / 2, start_y - i * line_h, ln)

        y -= mod_box_h + 50

        # ── Bas de page ──
        pdf.setStrokeColor(C.GOLD)
        pdf.setLineWidth(1.0)
        pdf.line(margin, y - 20, width - margin, y - 20)
        pdf.setFillColor(C.TXT_LIGHT)
        pdf.setFont("Helvetica", 12)
        pdf.drawCentredString(width / 2, y - 35,
            f"{self.examen.annee.annee_universitaire}")

    # ═══════════════════════════════════════════════════════════════════════════
    # PAGE 2 — Décharge
    # ═══════════════════════════════════════════════════════════════════════════
    def draw_page_two(self, pdf, width, height):
        margin = 55
        y = height - 45

        y = draw_logo_header(pdf, width, y, self._logo)

        # ── DECHARGE ──
        b1_h = 32
        draw_double_bordered_box(pdf, margin, y - b1_h, width - 2 * margin, b1_h,
                                 fill_color=C.NAVY, line_width=0.8, border_color=C.NAVY)
        pdf.setFillColor(C.WHITE)
        pdf.setFont("Helvetica-Bold", 19)
        pdf.drawCentredString(width / 2, y - 20, "DECHARGE")
        y -= b1_h + 8

        # ── Session box ──
        box_h = 55
        draw_double_bordered_box(pdf, margin, y - box_h, width - 2 * margin, box_h,
                                 fill_color=C.BG_LIGHT, line_width=0.8, border_color=C.BORDER)
        pdf.setFillColor(C.NAVY)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawCentredString(width / 2, y - 20,
            f"EXAMEN DES {self._semester_label()} - SESSION {self._session_label()}")

        # ← date_fr() ici (mois + année seulement)
        pdf.setFillColor(C.TXT_MED)
        pdf.setFont("Helvetica", 10)
        pdf.drawCentredString(width / 2, y - 38,
            f"SESSION {date_fr(self.examen.date, fmt='month').upper()}")
        y -= box_h + 28

        # ── MODULE ──
        pdf.setFillColor(C.NAVY)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(margin, y, "MODULE : ")
        pdf.setFillColor(C.TXT_DARK)
        pdf.setFont("Helvetica", 11)
        module_text = self.examen.module.upper()
        pdf.drawString(margin + 80, y, module_text)
        module_text_width = pdf.stringWidth(module_text, "Helvetica", 11)
        pdf.setStrokeColor(C.BORDER_LITE)
        pdf.setLineWidth(0.8)
        pdf.line(margin + 80, y - 3, margin + 80 + module_text_width, y - 3)
        y -= 25

        # ── SALLE ──
        pdf.setFillColor(C.NAVY)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawString(margin, y, "SALLE : ")
        pdf.setFillColor(C.TXT_DARK)
        pdf.setFont("Helvetica", 11)
        salle_text = self.amphi.nom.upper()
        pdf.drawString(margin + 70, y, salle_text)
        salle_text_width = pdf.stringWidth(salle_text, "Helvetica", 11)
        pdf.setStrokeColor(C.BORDER_LITE)
        pdf.line(margin + 70, y - 3, margin + 70 + salle_text_width, y - 3)
        y -= 30

        # ── Tableau stats ──
        total, participants, absents, duration = self._stats()
        y = draw_table_with_borders(pdf, margin, y,
            [135, 95, 90, 80, 100],
            [["EPREUVE", "INSCRITS", "PARTICIPANTS", "ABSENTS", "DUREE"],
             [self.examen.module.upper(), str(total), "", "", duration]],
            row_height=38)
        y -= 28

        # ── Tableau surveillants ──
        y = draw_table_with_borders(pdf, margin, y,
            [135, 155, 105, 107],
            [["MATIERE", "NOMS ET PRENOMS DES\nSURVEILLANTS", "SIGNATURES", "OBSERVATIONS"],
             ["", "", "", ""],
             ["", "", "", ""],
             ["", "", "", ""]],
            row_height=42,
            is_surveillant_table=True,
            merge_module=True,
            module_text=self.examen.module.upper())

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
        pdf.drawCentredString(width / 2, y,
            "FACULTE DE MEDECINE ET DE PHARMACIE LAAYOUNE")
        y -= 20
        pdf.setFillColor(C.TXT_MED)
        pdf.setFont("Helvetica", 10)
        pdf.drawCentredString(width / 2, y,
            f"ANNEE UNIVERSITAIRE {self.examen.annee.annee_universitaire}")
        y -= 35

        # ── PROCES VERBAL ──
        b1_h = 32
        draw_double_bordered_box(pdf, margin, y - b1_h, width - 2 * margin, b1_h,
                                 fill_color=C.NAVY, line_width=0.8, border_color=C.NAVY)
        pdf.setFillColor(C.WHITE)
        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawCentredString(width / 2, y - 20,
            "PROCES VERBAL DES EPREUVES ECRITES")
        y -= b1_h + 8

        # ── Session box ──
        b2_h = 48
        draw_double_bordered_box(pdf, margin, y - b2_h, width - 2 * margin, b2_h,
                                 fill_color=C.BG_LIGHT, line_width=0.8, border_color=C.BORDER)
        pdf.setFillColor(C.NAVY)
        pdf.setFont("Helvetica-Bold", 11)
        pdf.drawCentredString(width / 2, y - 16,
            f"EXAMEN DES {self._semester_label()} - SESSION {self._session_label()}")

        # ← date_fr() ici (mois + année)
        pdf.setFillColor(C.TXT_MED)
        pdf.setFont("Helvetica", 10)
        pdf.drawCentredString(width / 2, y - 32,
            date_fr(self.examen.date, fmt='month').upper())
        y -= b2_h + 20

        # ── MODULE ──
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

        # ── SALLE ──
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

        # ── Tableau stats ──
        total, participants, absents, duration = self._stats()
        y = draw_table_with_borders(pdf, margin, y,
            [135, 95, 90, 80, 100],
            [["EPREUVE", "INSCRITS", "PARTICIPANTS", "ABSENTS", "DUREE"],             
              [self.examen.module.upper(), str(total), "", "", duration]],
            row_height=38)
        y -= 25

        # ── Tableau surveillants ──
        y = draw_table_with_borders(pdf, margin, y,
            [135, 155, 105, 107],
            [["MATIERE", "NOMS ET PRENOMS DES\nSURVEILLANTS", "SIGNATURES", "OBSERVATIONS"],
             ["", "", "", ""],
             ["", "", "", ""],
             ["", "", "", ""]],
            row_height=42,
            is_surveillant_table=True,
            merge_module=True,
            module_text=self.examen.module.upper())

        today = datetime.now().strftime("%d/%m/%Y")
        pdf.setFillColor(C.TXT_MED)
        pdf.setFont("Helvetica", 9)
        pdf.drawRightString(width - margin, 60, f"LAAYOUNE, LE {today}")