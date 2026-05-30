# salles/models.py
from django.db import models
import qrcode
from io import BytesIO
from django.core.files import File
import os

class Amphi(models.Model):
    nom = models.CharField(max_length=50)
    capacite = models.IntegerField()

    def __str__(self):
        return self.nom
    
    def generate_all_seat_qrs(self):
        """Generate QR codes for all seats (1 to capacite)"""
        created = 0
        for seat_num in range(1, self.capacite + 1):
            seat, created_flag = Seat.objects.get_or_create(
                amphi=self,
                seat_number=seat_num
            )
            if created_flag:
                # Generate QR code for new seat
                seat.generate_qr_code()
                seat.save()
                created += 1
            elif not seat.qr_code:
                # If seat exists but no QR code, generate it
                seat.generate_qr_code()
                seat.save()
                created += 1
        return created

class Seat(models.Model):
    amphi = models.ForeignKey(Amphi, on_delete=models.CASCADE, related_name='seats')
    seat_number = models.IntegerField()
    qr_code = models.ImageField(upload_to='qr_codes/seats/', blank=True, null=True)
    
    class Meta:
        unique_together = ['amphi', 'seat_number']
        ordering = ['seat_number']
    
    def __str__(self):
        return f"{self.amphi.nom} - Seat {self.seat_number}"
    
    def generate_qr_code(self):
        """Generate QR code for this specific seat"""
        from io import BytesIO
        import qrcode
        
        # Simple QR data - just seat identification
        qr_data = f"Amphi: {self.amphi.nom} | Seat: {self.seat_number}"
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Create image
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Save to ImageField
        buffer = BytesIO()
        qr_image.save(buffer, format='PNG')
        buffer.seek(0)
        
        filename = f"seat_{self.amphi.id}_{self.seat_number}.png"
        self.qr_code.save(filename, File(buffer), save=False)