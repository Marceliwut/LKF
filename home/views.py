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



# Run the script
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def update_posters(request):
    """Update poster URLs in the CSV file using a user-provided TMDb API key."""
    if request.method == "POST":
        try:
            # Get the TMDb API key from the POST request
            data = json.loads(request.body)
            tmdb_api_key = data.get("tmdb_api_key")

            if not tmdb_api_key:
                return JsonResponse({"status": "error", "message": "TMDb API key is required."})

            # Update the poster URLs in the CSV file
            updated_rows = []
            with open(CSV_FILE_PATH, "r", encoding="utf-8") as csvfile:
                reader = csv.reader(csvfile)
                rows = list(reader)

                if len(rows) > 0:
                    header = rows[0]
                    if "Poster URL" not in header:
                        header.append("Poster URL")
                    updated_rows.append(header)

                    for row in rows[1:]:
                        while len(row) < len(header):
                            row.append("")

                        title = row[1] if len(row) > 1 else None
                        year = row[2] if len(row) > 2 else None

                        if not row[-1] and title and year:
                            try:
                                response = requests.get(TMDB_BASE_URL, params={
                                    "api_key": tmdb_api_key,
                                    "query": title,
                                    "year": year
                                })
                                if response.status_code == 200:
                                    results = response.json().get("results", [])
                                    if results:
                                        poster_path = results[0].get("poster_path")
                                        if poster_path:
                                            row[-1] = f"https://image.tmdb.org/t/p/w500{poster_path}"
                            except Exception as e:
                                print(f"Error fetching poster for {title} ({year}): {e}")
                                row[-1] = "N/A"

                        updated_rows.append(row)

            # Save the updated rows back to the CSV file
            with open(CSV_FILE_PATH, "w", encoding="utf-8", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerows(updated_rows)

            return JsonResponse({"status": "success", "message": "Poster URLs updated successfully."})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Invalid request method."})

def index(request):
    csv_file_path = os.path.join(settings.MEDIA_ROOT, 'data.csv')
    filter_by = request.GET.get('filter', 'not_watched')
    sort_by = request.GET.get('sort')
    search_query = request.GET.get('search', '').strip().lower()  # Get the search query
    
    # Initialize statistics
    watched_count = skipped_count = unwatched_count = 0
    total_duration_minutes = 0
    updated_rows = []
    header = []  # Initialize header to avoid UnboundLocalError

    if os.path.exists(csv_file_path):
        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)

            if len(rows) > 1:  # Ensure there are rows beyond the header
                header, data = rows[0], rows[1:]

                # Update statistics
                watched_count = sum(1 for row in data if len(row) > 9 and row[9] == 'TRUE')
                skipped_count = sum(1 for row in data if len(row) > 10 and row[10] == 'TRUE')
                unwatched_count = sum(1 for row in data if len(row) > 10 and row[9] != 'TRUE' and row[10] != 'TRUE')
                total_duration_minutes = sum(
                    parse_duration(row[3]) for row in data if len(row) > 3
                )

                # Apply filters
                if filter_by == 'watched':
                    updated_rows = [row for row in data if len(row) > 9 and row[9] == 'TRUE']
                elif filter_by == 'skipped':
                    updated_rows = [row for row in data if len(row) > 10 and row[10] == 'TRUE']
                elif filter_by == 'not_watched':
                    updated_rows = [row for row in data if len(row) > 10 and row[9] != 'TRUE' and row[10] != 'TRUE']
                else:
                    updated_rows = data

                # Apply search filter
                if search_query:
                    updated_rows = [row for row in updated_rows if search_query in row[1].lower()]

                # Apply sorting
                if not sort_by:
                    sort_by = 'desc' if filter_by == 'not_watched' else 'asc'

                if sort_by == 'asc':
                    updated_rows = sorted(updated_rows, key=lambda x: int(x[0]) if x[0].isdigit() else 0)
                elif sort_by == 'desc':
                    updated_rows = sorted(updated_rows, key=lambda x: int(x[0]) if x[0].isdigit() else 0, reverse=True)
            else:
                # If the CSV file is empty or invalid, initialize header and updated_rows
                header = ["Number", "Title", "Year", "Duration", "Age Rating", "Rating", "Votes", "Metascore", "Description", "Watched", "Skipped", "Series", "Poster URL"]
                updated_rows = []

    # Convert total duration to hours
    total_duration_hours = total_duration_minutes // 60
    total_duration_minutes_remainder = total_duration_minutes % 60

    return render(request, 'pages/dashboard.html', {
        'csv_data': [header] + updated_rows,
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
            field = data.get("field")  # Field to update (watched or skipped)

            # Debugging
            print(f"Request data: ID={entry_id}, Field={field}")

            # Load the current CSV data
            csv_data = load_csv_from_file()

            # Ensure the CSV data is not empty
            if not csv_data or len(csv_data) < 2:
                return JsonResponse({"status": "error", "message": "CSV data is empty or invalid."})

            # Debugging: Print the CSV data
            print("CSV Data:", csv_data)

            # Update the specific entry
            header, rows = csv_data[0], csv_data[1:]  # Separate header and rows
            updated = False

            for row in rows:
                print(f"Checking row: {row}")  # Debugging
                if row[0] == entry_id:  # Match the entry by ID
                    if field == "watched":
                        row[9] = "TRUE" if row[9] != "TRUE" else "FALSE"
                    elif field == "skipped":
                        row[10] = "TRUE" if row[10] != "TRUE" else "FALSE"
                    updated = True
                    break  # Break once the entry is updated

            if not updated:
                return JsonResponse({"status": "error", "message": f"Entry with ID {entry_id} not found."})

            # Save the updated data back to the file
            save_csv_to_file([header] + rows)
            return JsonResponse({"status": "success", "message": f"Film  {entry_id} updated to {field}."})
        except Exception as e:
            print("Error:", e)  # Debugging
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


def recommend_next_watch(request):
    """Recommend the next movie to watch."""
    try:
        # Load the CSV file
        csv_file_path = os.path.join(settings.MEDIA_ROOT, 'data.csv')
        if not os.path.exists(csv_file_path):
            return render(request, 'pages/recommend_next_watch.html', {'error': 'CSV file not found.'})

        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)

        if len(rows) <= 1:
            return render(request, 'pages/recommend_next_watch.html', {'error': 'No movies available for recommendation.'})

        # Exclude watched or skipped movies
        header, data = rows[0], rows[1:]
        unwatched_movies = [row for row in data if len(row) > 9 and row[9] != 'TRUE' and row[10] != 'TRUE']

        if not unwatched_movies:
            return render(request, 'pages/recommend_next_watch.html', {'error': 'No unwatched movies available for recommendation.'})

        # Find the next movie with the highest number (row[0])
        next_movie = max(unwatched_movies, key=lambda x: int(x[0]) if x[0].isdigit() else 0)

        # Find the shortest movie
        shortest_movie = min(unwatched_movies, key=lambda x: parse_duration(x[3]))

        # Calculate total duration
        total_duration_minutes = parse_duration(next_movie[3]) + parse_duration(shortest_movie[3])
        total_hours = total_duration_minutes // 60
        total_minutes = total_duration_minutes % 60

        recommendations = {
            'latest': {
                'id': next_movie[0],
                'title': next_movie[1],
                'year': next_movie[2],
                'duration': next_movie[3],
                'description': next_movie[8],
            },
            'shortest': {
                'id': shortest_movie[0],
                'title': shortest_movie[1],
                'year': shortest_movie[2],
                'duration': shortest_movie[3],
                'description': shortest_movie[8],
            },
        }

        return render(request, 'pages/recommend_next_watch.html', {
            'recommendations': recommendations,
            'total_hours': total_hours,
            'total_minutes': total_minutes,
        })

    except Exception as e:
        return render(request, 'pages/recommend_next_watch.html', {'error': str(e)})

def parse_duration(duration):
    """Parse duration in the format 'Xh Ym' and return total minutes."""
    match = re.match(r'(?:(\d+)h)?\s*(?:(\d+)m)?', duration)
    if match:
        hours = int(match.group(1)) if match.group(1) else 0
        minutes = int(match.group(2)) if match.group(2) else 0
        return hours * 60 + minutes
    return 0  # Return 0 if the format is invalid
@csrf_exempt
def find_next_shortest_movie(request):
    try:
        if request.method != "POST":
            return JsonResponse({"status": "error", "message": "Invalid request method."})

        # Load the CSV file
        csv_file_path = os.path.join(settings.MEDIA_ROOT, 'data.csv')
        if not os.path.exists(csv_file_path):
            return JsonResponse({"status": "error", "message": "CSV file not found."})

        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)

        if len(rows) <= 1:
            return JsonResponse({"status": "error", "message": "No movies available."})

        # Exclude watched or skipped movies
        header, data = rows[0], rows[1:]
        unwatched_movies = [row for row in data if len(row) > 9 and row[9] != 'TRUE' and row[10] != 'TRUE']

        if not unwatched_movies:
            return JsonResponse({"status": "error", "message": "No unwatched movies available."})

        # Get the currently displayed shortest movie ID from the request
        current_shortest_id = json.loads(request.body).get("current_shortest_id")

        # Exclude the currently displayed shortest movie
        if current_shortest_id:
            unwatched_movies = [row for row in unwatched_movies if row[0] != current_shortest_id]

        if not unwatched_movies:
            return JsonResponse({"status": "error", "message": "No other unwatched movies available."})

        # Find the next in line movie (highest ID)
        next_in_line_movie = max(unwatched_movies, key=lambda x: int(x[0]) if x[0].isdigit() else 0)

        # Target duration is 4.5 hours (270 minutes)
        target_duration = 270
        next_in_line_duration = parse_duration(next_in_line_movie[3])

        # Find the movie that, when summed with the next in line movie, is closest to 270 minutes
        best_match = min(
            unwatched_movies,
            key=lambda x: abs((parse_duration(x[3]) + next_in_line_duration) - target_duration)
        )

        # Calculate the total duration
        total_minutes = parse_duration(next_in_line_movie[3]) + parse_duration(best_match[3])
        total_hours = total_minutes // 60
        remaining_minutes = total_minutes % 60

        return JsonResponse({
            "status": "success",
            "movie": {
                "id": best_match[0],
                "title": best_match[1],
                "year": best_match[2],
                "duration": best_match[3],
                "description": best_match[8],
            },
            "total_duration": {
                "hours": total_hours,
                "minutes": remaining_minutes
            }
        })

    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})


def parse_duration(duration):
    """Parse a duration string like '1h 48m' into total minutes."""
    match = re.match(r'(?:(\d+)h)?\s*(?:(\d+)m)?', duration)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    return hours * 60 + minutes