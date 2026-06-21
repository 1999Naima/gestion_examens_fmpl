# salles/management/commands/generate_sieges.py
from django.core.management.base import BaseCommand
from salles.models import Amphi, siege

class Command(BaseCommand):
    help = 'Generate sieges for all amphitheaters'
    
    def add_arguments(self, parser):
        parser.add_argument('--amphi_id', type=int, help='Generate sieges for specific amphi')
        parser.add_argument('--force', action='store_true', help='Delete existing sieges and regenerate')
    
    def handle(self, *args, **options):
        if options['amphi_id']:
            amphis = Amphi.objects.filter(id=options['amphi_id'])
        else:
            amphis = Amphi.objects.all()
        
        for amphi in amphis:
            self.stdout.write(f"Processing {amphi.nom}...")
            
            if options['force']:
                # Delete existing sieges
                deleted = siege.objects.filter(amphi=amphi).delete()
                self.stdout.write(f"  Deleted existing sieges")
            
            existing_count = siege.objects.filter(amphi=amphi).count()
            
            if existing_count >= amphi.capacite:
                self.stdout.write(f"  Already has {existing_count} sieges (capacity: {amphi.capacite})")
                continue
            
            # Generate sieges
            sieges_to_create = []
            for siege_num in range(1, amphi.capacite + 1):
                if not siege.objects.filter(amphi=amphi, siege_number=siege_num).exists():
                    sieges_to_create.append(siege(amphi=amphi, siege_number=siege_num))
            
            if sieges_to_create:
                siege.objects.bulk_create(sieges_to_create)
                self.stdout.write(self.style.SUCCESS(f"  Created {len(sieges_to_create)} sieges"))
            else:
                self.stdout.write(f"  No new sieges to create")
        
        self.stdout.write(self.style.SUCCESS("Done!"))