from django.shortcuts import render
from django.http import JsonResponse
import requests
import csv
import os
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
import shutil
from datetime import datetime
from django.shortcuts import render
from django.conf import settings
import re

# Define the path for the CSV file
from django.conf import settings
CSV_FILE_PATH = os.path.join(settings.MEDIA_ROOT, 'data.csv')
BACKUP_DIR = os.path.join(settings.MEDIA_ROOT, 'backups')


def index(request):
    csv_data = load_csv_from_file()
    filter_by = request.GET.get('filter', 'not_watched')
    sort_by = request.GET.get('sort')
    search_query = request.GET.get('search', '').strip().lower()  # Get the search query

    # Initialize statistics
    watched_count = skipped_count = unwatched_count = 0
    total_duration_minutes = 0

    if csv_data and len(csv_data) > 1:
        header, rows = csv_data[0], csv_data[1:]

        # Calculate statistics safely
        watched_count = sum(1 for row in rows if len(row) > 9 and row[9] == 'TRUE')
        skipped_count = sum(1 for row in rows if len(row) > 10 and row[10] == 'TRUE')
        unwatched_count = sum(1 for row in rows if len(row) > 10 and row[9] != 'TRUE' and row[10] != 'TRUE')

        # Calculate total duration in minutes
        total_duration_minutes = sum(
            int(row[3]) for row in rows if len(row) > 3 and row[3].isdigit()
        )

        display_rows = rows

        # Apply filters
        if filter_by == 'watched':
            display_rows = [row for row in rows if len(row) > 9 and row[9] == 'TRUE']
        elif filter_by == 'skipped':
            display_rows = [row for row in rows if len(row) > 10 and row[10] == 'TRUE']
        elif filter_by == 'not_watched':
            display_rows = [row for row in rows if len(row) > 10 and row[9] != 'TRUE' and row[10] != 'TRUE']

        # Apply search filter
        if search_query:
            display_rows = [row for row in display_rows if search_query in row[1].lower()]

        # Apply sorting
        if not sort_by:
            sort_by = 'desc' if filter_by == 'not_watched' else 'asc'

        if sort_by == 'asc':
            display_rows = sorted(display_rows, key=lambda x: int(x[0]) if x[0].isdigit() else 0)
        elif sort_by == 'desc':
            display_rows = sorted(display_rows, key=lambda x: int(x[0]) if x[0].isdigit() else 0, reverse=True)

        csv_data = [header] + display_rows

    # Convert total duration to hours
    total_duration_hours = total_duration_minutes // 60
    total_duration_minutes_remainder = total_duration_minutes % 60

    return render(request, 'pages/dashboard.html', {
        'csv_data': csv_data,
        'watched_count': watched_count,
        'skipped_count': skipped_count,
        'unwatched_count': unwatched_count,
        'total_duration_hours': total_duration_hours,
        'total_duration_minutes_remainder': total_duration_minutes_remainder,
        'search_query': search_query,  # Pass the search query to the template
    })





def refresh_csv_data(request):
    try:
        # Download CSV data and save it to the file
        csv_data = get_csv_data()
        save_csv_to_file(csv_data)  # Save the data to a file
        return JsonResponse({'status': 'success', 'message': 'Data refreshed and saved to file!'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


def get_csv_data():
    print("Downloading CSV data...")

    # Replace this with the actual URL of your CSV file
    file_url = 'https://1drv.ms/x/c/e8caa386cc70b3e6/EQj6vRNxHBhDjTbOZdKcI8sBIrRLcnH59LIH34XLcVu1Qg?e=crEeXI&download=1'

    try:
        # Download the CSV file
        response = requests.get(file_url)
        response.raise_for_status()

        # Parse the CSV data
        csv_data = []
        reader = csv.reader(response.text.splitlines())
        for row in reader:
            csv_data.append(row)

        print("CSV data downloaded successfully!")
        return csv_data
    except requests.exceptions.RequestException as e:
        print(f"Error downloading file: {e}")
        raise e
    except csv.Error as e:
        print(f"Error processing CSV file: {e}")
        raise e


def save_csv_to_file(csv_data):
    """Save the CSV data to a file."""
    with open(CSV_FILE_PATH, "w", newline='', encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(csv_data)
    print(f"CSV data saved to {CSV_FILE_PATH}")


def load_csv_from_file():
    """Load CSV data from a file."""
    if os.path.exists(CSV_FILE_PATH):
        print(f"Loading data from {CSV_FILE_PATH}...")
        try:
            with open(CSV_FILE_PATH, "r", encoding="utf-8") as file:
                reader = csv.reader(file)
                csv_data = [row for row in reader]
                print("CSV data loaded successfully!")
                return csv_data
        except csv.Error as e:
            print(f"Error reading CSV file: {e}")
    else:
        print(f"{CSV_FILE_PATH} does not exist. Returning empty data.")
        return []
    
@csrf_exempt
def update_entry(request):
    if request.method == "POST":
        try:
            # Parse the request payload
            data = json.loads(request.body)
            entry_id = str(data.get("id"))  # Entry ID as a string
            entry_title = str(data.get("title"))  # Entry title as a string
            field = data.get("field")  # Field to update (watched or skipped)

            # Load the current CSV data
            csv_data = load_csv_from_file()

            # Ensure the CSV data is not empty
            if not csv_data or len(csv_data) < 2:
                return JsonResponse({"status": "error", "message": "CSV data is empty or invalid."})

            # Update the specific entry
            header, rows = csv_data[0], csv_data[1:]  # Separate header and rows
            updated = False

            for row in rows:
                if row[0] == entry_id:  # Match the entry by ID
                    if field == "watched":
                        row[9] = "TRUE" if row[9] != "TRUE" else "FALSE"
                    elif field == "skipped":
                        row[10] = "TRUE" if row[10] != "TRUE" else "FALSE"
                    updated = True
                    break  # Break once the entry is updated

            if not updated:
                return JsonResponse({"status": "error", "message": f"Entry with ID {entry_title} not found."})

            # Save the updated data back to the file
            save_csv_to_file([header] + rows)
            print("All good!!!")
            return JsonResponse({"status": "success", "message": f"Entry {entry_title} updated to {field}."})
        except Exception as e:
            print("Issue!!")
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Invalid request method."})


def backup_csv(request):
    if request.method == "POST":
        try:
            # Ensure the backup directory exists
            if not os.path.exists(BACKUP_DIR):
                os.makedirs(BACKUP_DIR)

            # Generate a filename with the current date and time
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            backup_file = os.path.join(BACKUP_DIR, f"backup_{timestamp}.csv")

            # Copy the file to the backup directory
            if os.path.exists(CSV_FILE_PATH):
                shutil.copy(CSV_FILE_PATH, backup_file)
                return JsonResponse({"status": "success", "message": f"Backup created: {backup_file}"})
            else:
                return JsonResponse({"status": "error", "message": f"Source file not found: {CSV_FILE_PATH}"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Invalid request method."})

from django.shortcuts import render
from django.conf import settings
import os

def file_explorer(request):
    """List files and directories in the media folder."""
    # Get the current path from the query parameter (default to the media root)
    current_path = request.GET.get('path', '')
    absolute_path = os.path.join(settings.MEDIA_ROOT, current_path)

    # Ensure the path is within the media directory
    if not absolute_path.startswith(settings.MEDIA_ROOT):
        return render(request, 'pages/file_explorer.html', {
            'error': 'Invalid path.',
            'files_and_dirs': [],
        })

    files_and_dirs = []

    try:
        # List all files and directories in the current path
        for item in os.listdir(absolute_path):
            item_path = os.path.join(absolute_path, item)
            files_and_dirs.append({
                'name': item,
                'is_file': os.path.isfile(item_path),
                'is_csv': os.path.isfile(item_path) and item.endswith('.csv'),  # Add CSV flag
                'url': f"{settings.MEDIA_URL}{current_path}/{item}" if os.path.isfile(item_path) else None,
                'path': os.path.join(current_path, item) if not os.path.isfile(item_path) else None,
            })
    except Exception as e:
        return render(request, 'pages/file_explorer.html', {
            'error': str(e),
            'files_and_dirs': [],
        })

    return render(request, 'pages/file_explorer.html', {
        'files_and_dirs': files_and_dirs,
        'current_path': current_path,
        'parent_path': os.path.dirname(current_path) if current_path else None,
    })

@csrf_exempt
def restore_backup(request):
    """Restore a backup file to /media/data.csv."""
    if request.method == "POST":
        try:
            # Get the filename from the POST request
            filename = request.POST.get('filename')
            if not filename:
                return JsonResponse({"status": "error", "message": "No filename provided."})

            # Construct the source and destination paths
            source_path = os.path.join(settings.MEDIA_ROOT, 'backups', filename)
            destination_path = os.path.join(settings.MEDIA_ROOT, 'data.csv')

            # Ensure the source file exists
            if not os.path.exists(source_path):
                return JsonResponse({"status": "error", "message": "Backup file not found."})

            # Copy the backup file to /media/data.csv
            shutil.copy(source_path, destination_path)

            return JsonResponse({"status": "success", "message": f"Backup {filename} restored to data.csv."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Invalid request method."})


def parse_duration(duration):
    """Parse duration in the format 'Xh XXminutes' and return total minutes."""
    match = re.match(r'(?:(\d+)h)?\s*(?:(\d+)minutes)?', duration)
    if match:
        hours = int(match.group(1)) if match.group(1) else 0
        minutes = int(match.group(2)) if match.group(2) else 0
        return hours * 60 + minutes
    return float('inf')  # Return a very large value if the format is invalid

def recommend_next_watch(request):
    """Recommend the next movie to watch."""
    csv_file_path = os.path.join(settings.MEDIA_ROOT, 'data.csv')
    recommendations = {"latest": None, "shortest": None}

    try:
        # Load the CSV file
        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)

            if len(rows) > 1:  # Ensure there are rows beyond the header
                header, data = rows[0], rows[1:]

                # Filter movies that are not watched and not skipped
                not_watched = [
                    row for row in data
                    if len(row) > 10 and row[9] != 'TRUE' and row[10] != 'TRUE'
                ]

                if not_watched:
                    # Find the latest movie (highest number)
                    recommendations["latest"] = max(
                        not_watched, key=lambda x: int(x[0]) if x[0].isdigit() else 0
                    )

                    # Exclude the latest movie from the shortest movie calculation
                    not_watched_excluding_latest = [
                        row for row in not_watched if row != recommendations["latest"]
                    ]

                    # Find the shortest movie (minimum duration)
                    if not_watched_excluding_latest:
                        recommendations["shortest"] = min(
                            not_watched_excluding_latest,
                            key=lambda x: parse_duration(x[3]) if len(x) > 3 else float('inf')
                        )
    except Exception as e:
        return render(request, 'pages/recommend_next_watch.html', {
            "error": str(e),
            "recommendations": recommendations,
        })

    return render(request, 'pages/recommend_next_watch.html', {
        "recommendations": recommendations,
    })