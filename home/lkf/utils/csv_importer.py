import csv
from home.models import Media

def import_media_csv(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                Media.objects.create(
                    number=int(row['Number']),
                    title=row['Title'],
                    year=int(row['Year']),
                    duration=row['Duration'],
                    age_rating=row['Age Rating'],
                    rating=float(row['Rating']),
                    votes=int(row['Votes']),
                    metascore=int(row['Metascore']) if row['Metascore'] else None,
                    description=row['Description'],
                    watched=row['Watched'].lower() == 'true',
                    skipped=row['Skipped'].lower() == 'true',
                    series=row['Series'].lower() == 'true',
                )
        print("Data imported successfully")
    except Exception as e:
        print(f"Error importing data: {e}")
