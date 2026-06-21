# salles/views.py
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from .models import Amphi, siege
import zipfile
from io import BytesIO

@staff_member_required
def generate_sieges_view(request, amphi_id):
    amphi = get_object_or_404(Amphi, id=amphi_id)
    existing = siege.objects.filter(amphi=amphi).count()
    
    if existing < amphi.capacite:
        created = 0
        for i in range(1, amphi.capacite + 1):
            if not siege.objects.filter(amphi=amphi, siege_number=i).exists():
                siege.objects.create(amphi=amphi, siege_number=i)
                created += 1
        messages.success(request, f"Created {created} sieges for {amphi.nom}")
    else:
        messages.info(request, f"{amphi.nom} already has all {existing} sieges")
    
    return redirect('admin:salles_amphi_change', amphi_id)

@staff_member_required
def download_qrs_view(request, amphi_id):
    amphi = get_object_or_404(Amphi, id=amphi_id)
    
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zip_file:
        for siege in amphi.sieges.all():
            if siege.qr_code and siege.qr_code.path:
                try:
                    with open(siege.qr_code.path, 'rb') as f:
                        zip_file.writestr(f"{amphi.nom}_siege_{siege.siege_number}.png", f.read())
                except FileNotFoundError:
                    continue
    
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{amphi.nom}_qr_codes.zip"'
    return response