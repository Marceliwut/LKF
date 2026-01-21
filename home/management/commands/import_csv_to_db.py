"""
Management command to import CSV data into the Media Django model.

This command reads the CSV file and creates Media objects in the database
instead of relying on CSV file I/O.

Usage: python manage.py import_csv_to_db <csv_file_path>
Example: python manage.py import_csv_to_db media/data.csv
"""
import csv
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import os

from home.models import Media


class Command(BaseCommand):
    help = 'Import CSV data into Media model'

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_file',
            type=str,
            help='Path to CSV file relative to MEDIA_ROOT or absolute path',
        )
        parser.add_argument(
            '--skip-existing',
            action='store_true',
            help='Skip movies that already exist (by number)',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete all existing Media records before importing',
        )

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        skip_existing = options.get('skip_existing', False)
        clear_existing = options.get('clear', False)
        
        # Determine full path to CSV file
        if os.path.isabs(csv_file):
            csv_path = csv_file
        else:
            csv_path = os.path.join(settings.MEDIA_ROOT, csv_file)
        
        if not os.path.exists(csv_path):
            raise CommandError(f'CSV file not found: {csv_path}')
        
        # Clear existing data if requested
        if clear_existing:
            deleted_count, _ = Media.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(f'Deleted {deleted_count} existing Media records')
            )
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        error_count = 0
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                
                if not reader.fieldnames:
                    raise CommandError('CSV file is empty or invalid')
                
                # Expected columns
                expected_fields = {
                    'Number', 'Title', 'Year', 'Duration', 'Age Rating',
                    'Rating', 'Votes', 'Metascore', 'Description',
                    'Watched', 'Skipped', 'Series', 'Poster URL'
                }
                
                if not all(field in reader.fieldnames for field in expected_fields):
                    raise CommandError(
                        f'CSV must have columns: {expected_fields}'
                    )
                
                for row_num, row in enumerate(reader, start=2):  # Start at 2 (skip header)
                    try:
                        # Parse and validate data
                        try:
                            number = int(row['Number'].strip())
                        except (ValueError, AttributeError):
                            self.stdout.write(
                                self.style.ERROR(
                                    f'Row {row_num}: Invalid Number "{row.get("Number")}"'
                                )
                            )
                            error_count += 1
                            continue
                        
                        try:
                            year = int(row['Year'].strip())
                        except (ValueError, AttributeError):
                            self.stdout.write(
                                self.style.ERROR(
                                    f'Row {row_num}: Invalid Year "{row.get("Year")}"'
                                )
                            )
                            error_count += 1
                            continue
                        
                        try:
                            rating = float(row['Rating'].strip())
                        except (ValueError, AttributeError):
                            self.stdout.write(
                                self.style.ERROR(
                                    f'Row {row_num}: Invalid Rating "{row.get("Rating")}"'
                                )
                            )
                            error_count += 1
                            continue
                        
                        # Parse metascore (optional)
                        metascore = None
                        if row.get('Metascore', '').strip():
                            try:
                                metascore = int(row['Metascore'].strip())
                            except ValueError:
                                pass
                        
                        # Parse boolean fields
                        watched = row.get('Watched', 'FALSE').strip().upper() == 'TRUE'
                        skipped = row.get('Skipped', 'FALSE').strip().upper() == 'TRUE'
                        series = row.get('Series', 'FALSE').strip().upper() == 'TRUE'
                        
                        # Get or create Media object
                        media_data = {
                            'title': row['Title'].strip(),
                            'year': year,
                            'duration': row['Duration'].strip(),
                            'age_rating': row['Age Rating'].strip(),
                            'rating': rating,
                            'votes': row['Votes'].strip(),
                            'metascore': metascore,
                            'description': row['Description'].strip(),
                            'watched': watched,
                            'skipped': skipped,
                            'series': series,
                            'poster_url': row.get('Poster URL', '').strip() or None,
                        }
                        
                        media, created = Media.objects.update_or_create(
                            number=number,
                            defaults=media_data
                        )
                        
                        if created:
                            created_count += 1
                            self.stdout.write(
                                self.style.SUCCESS(
                                    f'✓ Created: {number}. {media.title} ({year})'
                                )
                            )
                        else:
                            if skip_existing:
                                skipped_count += 1
                            else:
                                updated_count += 1
                                self.stdout.write(
                                    self.style.WARNING(
                                        f'⟳ Updated: {number}. {media.title} ({year})'
                                    )
                                )
                    
                    except Exception as e:
                        error_count += 1
                        self.stdout.write(
                            self.style.ERROR(f'Row {row_num}: {str(e)}')
                        )
        
        except Exception as e:
            raise CommandError(f'Error reading CSV file: {str(e)}')
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Import complete!\n'
                f'  Created: {created_count}\n'
                f'  Updated: {updated_count}\n'
                f'  Skipped: {skipped_count}\n'
                f'  Errors: {error_count}\n'
                f'  Total in database: {Media.objects.count()}'
            )
        )
