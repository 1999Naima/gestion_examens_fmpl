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
        return "Not generated"
    qr_code_preview.short_description = "QR Code"

@admin.register(Amphi)
class AmphiAdmin(admin.ModelAdmin):
    list_display = ('nom', 'capacite', 'sieges_count', 'generate_qrs_button', 'download_qrs_button', 'print_pdf_button')
    inlines = [siegeInline]
    
    def sieges_count(self, obj):
        count = obj.sieges.count()
        return f"{count} / {obj.capacite}"
    sieges_count.short_description = "sieges with QR"
    
    def generate_qrs_button(self, obj):
        return format_html(
            '<a class="button" href="generate-qrs/{}/" style="background-color: #28a745;">Generate All QR Codes</a>',
            obj.id
        )
    generate_qrs_button.short_description = ""
    
    def download_qrs_button(self, obj):
        return format_html(
            '<a class="button" href="download-qrs/{}/" style="background-color: #17a2b8;">Download All QR Codes (ZIP)</a>',
            obj.id
        )
    download_qrs_button.short_description = ""
    
    def print_pdf_button(self, obj):
        return format_html(
            '<a class="button" href="print-pdf/{}/" style="background-color: #dc3545;">Print PDF (sieges + QR)</a>',
            obj.id
        )
    print_pdf_button.short_description = ""
    
    def get_urls(self):
        def generate_qrs(request, amphi_id):
            amphi = get_object_or_404(Amphi, pk=amphi_id)
            created = amphi.generate_all_siege_qrs()
            if created > 0:
                messages.success(request, f"Successfully generated {created} QR codes for {amphi.nom}")
            else:
                messages.info(request, f"All QR codes already exist for {amphi.nom}")
            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/salles/amphi/'))
        
        def download_qrs(request, amphi_id):
            amphi = get_object_or_404(Amphi, pk=amphi_id)
            
            # First generate any missing QR codes
            amphi.generate_all_siege_qrs()
            
            buffer = BytesIO()
            with zipfile.ZipFile(buffer, 'w') as zip_file:
                for siege in amphi.sieges.all():
                    if siege.qr_code and siege.qr_code.path:
                        try:
                            if os.path.exists(siege.qr_code.path):
                                with open(siege.qr_code.path, 'rb') as f:
                                    zip_file.writestr(f"{amphi.nom}_siege_{siege.siege_number}.png", f.read())
                        except Exception as e:
                            print(f"Error adding {siege}: {e}")
            
            buffer.seek(0)
            response = HttpResponse(buffer, content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{amphi.nom}_all_qr_codes.zip"'
            return response
        
        def print_pdf(request, amphi_id):
            amphi = get_object_or_404(Amphi, pk=amphi_id)
            
            # Generate any missing QR codes first
            amphi.generate_all_siege_qrs()
            
            # Create PDF
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{amphi.nom}_sieges_qrcodes.pdf"'
            
            # Create PDF with landscape A4
            pdf = canvas.Canvas(response, pagesize=landscape(A4))
            width, height = landscape(A4)
            
            # Define grid layout (4 columns x 5 rows = 20 sieges per page)
            cols = 4
            rows_per_page = 5
            cell_width = (width - 30) / cols
            cell_height = (height - 80) / rows_per_page
            
            # Get all sieges ordered by number
            sieges = amphi.sieges.all().order_by('siege_number')
            
            # Calculate total pages
            sieges_list = list(sieges)
            sieges_per_page = cols * rows_per_page
            total_pages = (len(sieges_list) + sieges_per_page - 1) // sieges_per_page
            
            # Get current date and time
            now = datetime.now()
            current_date = now.strftime("%Y-%m-%d %H:%M:%S")
            
            for page_num in range(total_pages):
                if page_num > 0:
                    pdf.showPage()
                
                # Add header
                pdf.setFont("Helvetica-Bold", 16)
                pdf.drawCentredString(width/2, height - 30, f"{amphi.nom} - sieges with QR Codes")
                pdf.setFont("Helvetica", 10)
                pdf.drawCentredString(width/2, height - 45, f"Total sieges: {len(sieges_list)} | Page {page_num + 1} of {total_pages}")
                
                # Draw grid lines and content
                start_idx = page_num * sieges_per_page
                end_idx = min(start_idx + sieges_per_page, len(sieges_list))
                
                for idx in range(start_idx, end_idx):
                    siege = sieges_list[idx]
                    local_idx = idx - start_idx
                    row = local_idx // cols
                    col = local_idx % cols
                    
                    x = 15 + (col * cell_width)
                    y = height - 80 - (row * cell_height)
                    
                    # Draw cell border
                    pdf.rect(x, y - cell_height + 15, cell_width - 5, cell_height - 15)
                    
                    # Add siege number
                    pdf.setFont("Helvetica-Bold", 14)
                    pdf.drawCentredString(x + (cell_width - 5)/2, y - 15, f"siege #{siege.siege_number}")
                    
                    # Add QR code if exists
                    if siege.qr_code and siege.qr_code.path and os.path.exists(siege.qr_code.path):
                        try:
                            # Calculate QR size (70% of cell width)
                            qr_size = min(cell_width - 20, cell_height - 50)
                            qr_x = x + (cell_width - 5 - qr_size) / 2
                            qr_y = y - cell_height + 35
                            
                            # Draw QR code
                            from reportlab.lib.utils import ImageReader
                            img_reader = ImageReader(siege.qr_code.path)
                            pdf.drawImage(img_reader, qr_x, qr_y, width=qr_size, height=qr_size)
                        except Exception as e:
                            pdf.setFont("Helvetica", 8)
                            pdf.drawCentredString(x + (cell_width - 5)/2, y - cell_height/2, "QR Error")
                    else:
                        pdf.setFont("Helvetica", 10)
                        pdf.drawCentredString(x + (cell_width - 5)/2, y - cell_height/2, "No QR Code")
                
                # Add footer
                pdf.setFont("Helvetica", 8)
                pdf.drawCentredString(width/2, 15, f"Generated on {current_date} | FMPL Exam Management System")
            
            pdf.save()
            return response
        
        custom_urls = [
            path('generate-qrs/<int:amphi_id>/', generate_qrs, name='generate_qrs'),
            path('download-qrs/<int:amphi_id>/', download_qrs, name='download_qrs'),
            path('print-pdf/<int:amphi_id>/', print_pdf, name='print_pdf'),
        ]
        return custom_urls + super().get_urls()

@admin.register(siege)
class siegeAdmin(admin.ModelAdmin):
    list_display = ('amphi', 'siege_number', 'qr_code_preview')
    list_filter = ('amphi',)
    
    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="50" height="50" />', obj.qr_code.url)
        return "No QR"
    qr_code_preview.short_description = "QR Code"