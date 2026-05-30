# salles/views.py
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from .models import Amphi, Seat
import zipfile
from io import BytesIO

@staff_member_required
def generate_seats_view(request, amphi_id):
    amphi = get_object_or_404(Amphi, id=amphi_id)
    existing = Seat.objects.filter(amphi=amphi).count()
    
    if existing < amphi.capacite:
        created = 0
        for i in range(1, amphi.capacite + 1):
            if not Seat.objects.filter(amphi=amphi, seat_number=i).exists():
                Seat.objects.create(amphi=amphi, seat_number=i)
                created += 1
        messages.success(request, f"Created {created} seats for {amphi.nom}")
    else:
        messages.info(request, f"{amphi.nom} already has all {existing} seats")
    
    return redirect('admin:salles_amphi_change', amphi_id)

@staff_member_required
def download_qrs_view(request, amphi_id):
    amphi = get_object_or_404(Amphi, id=amphi_id)
    
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w') as zip_file:
        for seat in amphi.seats.all():
            if seat.qr_code and seat.qr_code.path:
                try:
                    with open(seat.qr_code.path, 'rb') as f:
                        zip_file.writestr(f"{amphi.nom}_seat_{seat.seat_number}.png", f.read())
                except FileNotFoundError:
                    continue
    
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{amphi.nom}_qr_codes.zip"'
    return response