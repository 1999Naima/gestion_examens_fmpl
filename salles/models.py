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
    
    def generate_all_siege_qrs(self):
        created = 0
        for siege_num in range(1, self.capacite + 1):
            siege_obj, created_flag = siege.objects.get_or_create(
                amphi=self,
                siege_number=siege_num
            )
            if created_flag:
                siege_obj.generate_qr_code()
                siege_obj.save()
                created += 1
            elif not siege_obj.qr_code:
                siege_obj.generate_qr_code()
                siege_obj.save()
                created += 1
        return created

class siege(models.Model):
    amphi = models.ForeignKey(Amphi, on_delete=models.CASCADE, related_name='sieges')
    siege_number = models.IntegerField()
    qr_code = models.ImageField(upload_to='qr_codes/sieges/', blank=True, null=True)
    
    class Meta:
        unique_together = ['amphi', 'siege_number']
        ordering = ['siege_number']
    
    def __str__(self):
        return f"{self.amphi.nom} - siege {self.siege_number}"
    
    def generate_qr_code(self):
        """Generate QR code for this specific siege"""
        from io import BytesIO
        import qrcode
        
        # Simple QR data - just siege identification
        qr_data = f"Amphi: {self.amphi.nom} | siege: {self.siege_number}"
        
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
        
        filename = f"siege_{self.amphi.id}_{self.siege_number}.png"
        self.qr_code.save(filename, File(buffer), save=False)