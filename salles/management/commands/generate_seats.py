# salles/management/commands/generate_seats.py
from django.core.management.base import BaseCommand
from salles.models import Amphi, Seat

class Command(BaseCommand):
    help = 'Generate seats for all amphitheaters'
    
    def add_arguments(self, parser):
        parser.add_argument('--amphi_id', type=int, help='Generate seats for specific amphi')
        parser.add_argument('--force', action='store_true', help='Delete existing seats and regenerate')
    
    def handle(self, *args, **options):
        if options['amphi_id']:
            amphis = Amphi.objects.filter(id=options['amphi_id'])
        else:
            amphis = Amphi.objects.all()
        
        for amphi in amphis:
            self.stdout.write(f"Processing {amphi.nom}...")
            
            if options['force']:
                # Delete existing seats
                deleted = Seat.objects.filter(amphi=amphi).delete()
                self.stdout.write(f"  Deleted existing seats")
            
            existing_count = Seat.objects.filter(amphi=amphi).count()
            
            if existing_count >= amphi.capacite:
                self.stdout.write(f"  Already has {existing_count} seats (capacity: {amphi.capacite})")
                continue
            
            # Generate seats
            seats_to_create = []
            for seat_num in range(1, amphi.capacite + 1):
                if not Seat.objects.filter(amphi=amphi, seat_number=seat_num).exists():
                    seats_to_create.append(Seat(amphi=amphi, seat_number=seat_num))
            
            if seats_to_create:
                Seat.objects.bulk_create(seats_to_create)
                self.stdout.write(self.style.SUCCESS(f"  Created {len(seats_to_create)} seats"))
            else:
                self.stdout.write(f"  No new seats to create")
        
        self.stdout.write(self.style.SUCCESS("Done!"))