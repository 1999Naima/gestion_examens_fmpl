# salles/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.urls import path
from django.shortcuts import get_object_or_404
from .models import Amphi, siege
import zipfile
from io import BytesIO
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from PIL import Image


class siegeInline(admin.TabularInline):
    model = siege
    extra = 0
    fields = ('siege_number', 'qr_code_preview')
    readonly_fields = ('siege_number', 'qr_code_preview')

    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="50" height="50" />', obj.qr_code.url)
        return "Non généré"
    qr_code_preview.short_description = "QR Code"


@admin.register(Amphi)
class AmphiAdmin(admin.ModelAdmin):
    list_display = ('nom', 'capacite', 'sieges_count',
                    'generate_qrs_button', 'print_pdf_button')
    inlines = [siegeInline]

    class Media:
        css = {
            'all': ('https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',)
        }

    def sieges_count(self, obj):
        count = obj.sieges.count()
        pct   = int(count / obj.capacite * 100) if obj.capacite else 0
        color = '#2e7d32' if pct == 100 else '#e65100' if pct == 0 else '#1565c0'
        return format_html(
            '''
            <div style="display:flex;align-items:center;gap:8px;min-width:120px">
              <div style="flex:1;background:#e0e0e0;border-radius:99px;height:7px;overflow:hidden">
                <div style="width:{}%;background:{};height:100%;border-radius:99px;
                            transition:width .3s"></div>
              </div>
              <span style="font-size:12px;font-weight:600;color:{};">{}&nbsp;/&nbsp;{}</span>
            </div>
            ''',
            pct, color, color, count, obj.capacite
        )
    sieges_count.short_description = "Sièges / QR"

    def generate_qrs_button(self, obj):
        return format_html(
            '''
            <a href="generate-qrs/{}/"
               style="display:inline-flex;align-items:center;gap:6px;
                      padding:6px 14px;border-radius:8px;font-size:12px;font-weight:600;
                      text-decoration:none;color:#fff;
                      background:linear-gradient(135deg,#1a5276,#2e86c1);
                      box-shadow:0 2px 6px rgba(30,80,130,.35);
                      transition:all .2s;border:none;cursor:pointer;"
               onmouseover="this.style.background='linear-gradient(135deg,#154360,#1a5276)';
                            this.style.boxShadow='0 4px 12px rgba(30,80,130,.45)'"
               onmouseout="this.style.background='linear-gradient(135deg,#1a5276,#2e86c1)';
                           this.style.boxShadow='0 2px 6px rgba(30,80,130,.35)'">
              <i class="fas fa-qrcode"></i> Générer QR
            </a>
            ''',
            obj.id
        )
    generate_qrs_button.short_description = ""

    def print_pdf_button(self, obj):
        return format_html(
            '''
            <a href="print-pdf/{}/"
               style="display:inline-flex;align-items:center;gap:6px;
                      padding:6px 14px;border-radius:8px;font-size:12px;font-weight:600;
                      text-decoration:none;color:#fff;
                      background:linear-gradient(135deg,#7b241c,#c0392b);
                      box-shadow:0 2px 6px rgba(150,30,30,.35);
                      transition:all .2s;border:none;cursor:pointer;"
               onmouseover="this.style.background='linear-gradient(135deg,#641e16,#7b241c)';
                            this.style.boxShadow='0 4px 12px rgba(150,30,30,.45)'"
               onmouseout="this.style.background='linear-gradient(135deg,#7b241c,#c0392b)';
                           this.style.boxShadow='0 2px 6px rgba(150,30,30,.35)'">
              <i class="fas fa-file-pdf"></i> Imprimer PDF
            </a>
            ''',
            obj.id
        )
    print_pdf_button.short_description = ""

    def get_urls(self):
        def generate_qrs(request, amphi_id):
            amphi   = get_object_or_404(Amphi, pk=amphi_id)
            created = amphi.generate_all_siege_qrs()
            if created > 0:
                messages.success(
                    request,
                    f" {created} QR code(s) générés avec succès pour {amphi.nom}."
                )
            else:
                messages.info(
                    request,
                    f"ℹ️ Tous les QR codes existent déjà pour {amphi.nom}."
                )
            return HttpResponseRedirect(
                request.META.get('HTTP_REFERER', '/admin/salles/amphi/')
            )

        def download_qrs(request, amphi_id):
            amphi = get_object_or_404(Amphi, pk=amphi_id)
            amphi.generate_all_siege_qrs()

            buffer = BytesIO()
            with zipfile.ZipFile(buffer, 'w') as zip_file:
                for s in amphi.sieges.all():
                    if s.qr_code and s.qr_code.path:
                        try:
                            if os.path.exists(s.qr_code.path):
                                with open(s.qr_code.path, 'rb') as f:
                                    zip_file.writestr(
                                        f"{amphi.nom}_siege_{s.siege_number}.png",
                                        f.read()
                                    )
                        except Exception as e:
                            print(f"Erreur ajout {s}: {e}")

            buffer.seek(0)
            response = HttpResponse(buffer, content_type='application/zip')
            response['Content-Disposition'] = (
                f'attachment; filename="{amphi.nom}_all_qr_codes.zip"'
            )
            return response

        def print_pdf(request, amphi_id):
            amphi = get_object_or_404(Amphi, pk=amphi_id)
            amphi.generate_all_siege_qrs()

            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = (
                f'attachment; filename="{amphi.nom}_sieges_qrcodes.pdf"'
            )

            pdf = canvas.Canvas(response, pagesize=landscape(A4))
            width, height = landscape(A4)

            cols           = 4
            rows_per_page  = 5
            cell_width     = (width - 30) / cols
            cell_height    = (height - 80) / rows_per_page

            sieges_list    = list(amphi.sieges.all().order_by('siege_number'))
            sieges_per_page = cols * rows_per_page
            total_pages    = (len(sieges_list) + sieges_per_page - 1) // sieges_per_page
            current_date   = datetime.now().strftime("%d/%m/%Y %H:%M")

            for page_num in range(total_pages):
                if page_num > 0:
                    pdf.showPage()

                # ── Header ──
                pdf.setFillColorRGB(0.10, 0.23, 0.36)
                pdf.rect(0, height - 55, width, 55, stroke=0, fill=1)

                pdf.setFillColorRGB(1, 1, 1)
                pdf.setFont("Helvetica-Bold", 16)
                pdf.drawCentredString(
                    width / 2, height - 28,
                    f"{amphi.nom}  —  Sièges & QR Codes"
                )
                pdf.setFont("Helvetica", 10)
                pdf.drawCentredString(
                    width / 2, height - 45,
                    f"Total sièges : {len(sieges_list)}  |  "
                    f"Page {page_num + 1} / {total_pages}"
                )

                # ── Grid ──
                start_idx = page_num * sieges_per_page
                end_idx   = min(start_idx + sieges_per_page, len(sieges_list))

                for idx in range(start_idx, end_idx):
                    s         = sieges_list[idx]
                    local_idx = idx - start_idx
                    row       = local_idx // cols
                    col       = local_idx % cols

                    cx = 15 + col * cell_width
                    cy = height - 80 - row * cell_height

                    # Cell background (alternating)
                    bg = (0.97, 0.98, 1.0) if local_idx % 2 == 0 else (1, 1, 1)
                    pdf.setFillColorRGB(*bg)
                    pdf.roundRect(cx, cy - cell_height + 15,
                                  cell_width - 8, cell_height - 15,
                                  6, stroke=0, fill=1)

                    # Cell border
                    pdf.setStrokeColorRGB(0.78, 0.85, 0.93)
                    pdf.setLineWidth(0.8)
                    pdf.roundRect(cx, cy - cell_height + 15,
                                  cell_width - 8, cell_height - 15,
                                  6, stroke=1, fill=0)

                    cell_inner_w = cell_width - 8
                    cell_inner_h = cell_height - 15
                    cell_y_bot   = cy - cell_height + 15

                    # ── Left zone: big seat number ──
                    left_w = cell_inner_w * 0.42
                    # Vertical divider
                    pdf.setStrokeColorRGB(0.78, 0.85, 0.93)
                    pdf.setLineWidth(0.6)
                    pdf.line(cx + left_w, cell_y_bot + 10,
                             cx + left_w, cy - 10)

                    # "SIÈGE" label
                    pdf.setFillColorRGB(0.55, 0.65, 0.75)
                    pdf.setFont("Helvetica", 7)
                    pdf.drawCentredString(cx + left_w / 2, cy - 18, "SIÈGE")

                    # Big seat number
                    pdf.setFillColorRGB(0.10, 0.23, 0.36)
                    num_font_size = 38
                    pdf.setFont("Helvetica-Bold", num_font_size)
                    num_y = cell_y_bot + cell_inner_h / 2 - num_font_size / 2 + 4
                    pdf.drawCentredString(cx + left_w / 2, num_y,
                                         str(s.siege_number))

                    # ── Right zone: QR code ──
                    right_x  = cx + left_w + 6
                    right_w  = cell_inner_w - left_w - 8
                    qr_pad   = 10
                    qr_size  = min(right_w - qr_pad * 2,
                                   cell_inner_h - qr_pad * 2)
                    qr_x     = right_x + (right_w - qr_size) / 2
                    qr_y     = cell_y_bot + (cell_inner_h - qr_size) / 2

                    if (s.qr_code and s.qr_code.path
                            and os.path.exists(s.qr_code.path)):
                        try:
                            from reportlab.lib.utils import ImageReader
                            pdf.drawImage(
                                ImageReader(s.qr_code.path),
                                qr_x, qr_y,
                                width=qr_size, height=qr_size
                            )
                        except Exception:
                            pdf.setFillColorRGB(0.6, 0.6, 0.6)
                            pdf.setFont("Helvetica", 8)
                            pdf.drawCentredString(right_x + right_w / 2,
                                                  cell_y_bot + cell_inner_h / 2,
                                                  "Erreur QR")
                    else:
                        pdf.setFillColorRGB(0.6, 0.6, 0.6)
                        pdf.setFont("Helvetica", 9)
                        pdf.drawCentredString(right_x + right_w / 2,
                                              cell_y_bot + cell_inner_h / 2,
                                              "QR non généré")

                # ── Footer ──
                pdf.setFillColorRGB(0.95, 0.96, 0.98)
                pdf.rect(0, 0, width, 22, stroke=0, fill=1)
                pdf.setFillColorRGB(0.45, 0.55, 0.65)
                pdf.setFont("Helvetica", 8)
                pdf.drawCentredString(
                    width / 2, 7,
                    f"Généré le {current_date}  |  Système de Gestion des Examens FMPL"
                )

            pdf.save()
            return response

        custom_urls = [
            path('generate-qrs/<int:amphi_id>/', generate_qrs, name='generate_qrs'),
            path('download-qrs/<int:amphi_id>/', download_qrs, name='download_qrs'),
            path('print-pdf/<int:amphi_id>/',   print_pdf,     name='print_pdf'),
        ]
        return custom_urls + super().get_urls()


@admin.register(siege)
class siegeAdmin(admin.ModelAdmin):
    list_display = ('amphi', 'siege_number', 'qr_code_preview')
    list_filter  = ('amphi',)

    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html(
                '<img src="{}" width="50" height="50" '
                'style="border-radius:6px;border:1px solid #ddd;padding:2px"/>',
                obj.qr_code.url
            )
        return format_html(
            '<span style="color:#999;font-size:12px;font-style:italic">Non généré</span>'
        )
    qr_code_preview.short_description = "QR Code"