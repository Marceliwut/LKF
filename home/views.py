from django.shortcuts import render, redirect
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
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login as auth_login
from .forms import CustomLoginForm, CustomSignupForm, AdminResetPasswordForm, MovieProposalForm
from .models import MovieProposal, ProposalVote, LogEntry
from django.views.decorators.http import require_POST
from django.http import FileResponse
from django.conf import settings

@csrf_exempt
@require_POST
def clear_logs(request):
    """Admin: delete all log entries."""
    if not request.user.is_authenticated or request.user.username != 'admin':
        return JsonResponse({'status': 'error', 'message': 'Brak dostępu.'})
    
    try:
        from .models import LogEntry
        count = LogEntry.objects.count()
        LogEntry.objects.all().delete()
        log_action(request, 'clear_logs', details=f'Usunięto {count} logów')  # log samego czyszczenia
        return JsonResponse({
            'status': 'success', 
            'message': f'Usunięto {count} logów.'
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Błąd: {str(e)}'})




def download_sqlite(request):
    db_path = os.path.join(settings.BASE_DIR, 'db.sqlite3')
    return FileResponse(open(db_path, 'rb'), as_attachment=True, filename='db.sqlite3')

def log_action(request, action, proposal_id=None, proposal_title='', details=''):
    """Log user action to database."""
    from .models import LogEntry
    LogEntry.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action=action,
        proposal_id=proposal_id,
        proposal_title=proposal_title,
        details=details
    )



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

            # Update the specific entry
            header, rows = csv_data[0], csv_data[1:]  # Separate header and rows
            updated = False

            for row in rows:
                print(f"Checking row: {row}")  # Debugging
                if row[0] == entry_id:  # Match the entry by ID
                    if field == "watched":
                        row[9] = "TRUE" if row[9] != "TRUE" else "FALSE"  # Toggle "Oglądnięte"
                    elif field == "skipped":
                        row[10] = "TRUE" if row[10] != "TRUE" else "FALSE"  # Toggle "Skipnięte"
                    updated = True
                    break  # Break once the entry is updated

            if not updated:
                return JsonResponse({"status": "error", "message": f"Entry with ID {entry_id} not found."})

            # Save the updated data back to the file
            save_csv_to_file([header] + rows)
            return JsonResponse({"status": "success", "message": f"Film {entry_id} updated to {field}."})
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

def user(request):
   

    return render(request, 'pages/user.html', {
        
    })

def register(request):
   

    return render(request, 'pages/register.html', {
        
    })

def login(request):
   

    return render(request, 'pages/login.html', {
        
    })

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            log_action(request, 'login')
            return redirect('home')  # Redirect to home
            
        
    return render(request, 'pages/login.html')


def auth_signin(request):
    if request.method == 'POST':
        form = CustomLoginForm(request=request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            log_action(request, 'login')  # ← DODAJ
            return redirect('index')
    else:
        form = CustomLoginForm(request=request)
    return render(request, 'accounts/auth-signin.html', {'form': form})



def auth_signup(request):
    if request.method == 'POST':
        form = CustomSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            log_action(request, 'register')  # ← DODAJ
            return redirect('index')
    else:
        form = CustomSignupForm()
    return render(request, 'accounts/auth-signup.html', {'form': form})




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


def login_view(request):
    """Handle user login."""
    if request.method == 'POST':
        username_or_email = request.POST.get('username')
        password = request.POST.get('password')
        
        # Try to authenticate with username first
        user = authenticate(request, username=username_or_email, password=password)
        
        # If not found, try with email
        if user is None:
            try:
                user_obj = User.objects.get(email=username_or_email)
                user = authenticate(request, username=user_obj.username, password=password)
            except User.DoesNotExist:
                user = None
        
        if user is not None:
            auth_login(request, user)
            return render(request, 'pages/dashboard.html')
        else:
            error_message = "Błędna nazwa użytkownika/email lub hasło"
            return render(request, 'pages/login.html', {'error': error_message})
    
    return render(request, 'pages/login.html')


def register_view(request):
    """Handle user registration."""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        
        # Validate passwords match
        if password != password_confirm:
            error_message = "Hasła się nie zgadzają"
            return render(request, 'pages/register.html', {'error': error_message})
        
        # Validate password length
        if len(password) < 8:
            error_message = "Hasło musi mieć co najmniej 8 znaków"
            return render(request, 'pages/register.html', {'error': error_message})
        
        # Check if user already exists
        if User.objects.filter(username=username).exists():
            error_message = "Nazwa użytkownika już istnieje"
            return render(request, 'pages/register.html', {'error': error_message})
        
        if User.objects.filter(email=email).exists():
            error_message = "Email już jest zarejestrowany"
            return render(request, 'pages/register.html', {'error': error_message})
        
        # Create new user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password
        )
        
        # Log the user in automatically
        auth_login(request, user)
        log_action(request, 'register') 
        return render(request, 'pages/dashboard.html')
    
    return render(request, 'pages/register.html')


def admin_view(request):
    """Admin page to manage users - only accessible by 'admin' user."""
    # Check if user is authenticated and is the admin user
    if not request.user.is_authenticated or request.user.username != 'admin':
        return render(request, 'pages/dashboard.html', {
            'error': 'Brak dostępu. Tylko użytkownik admin może przeglądać tę stronę.'
        })
    
    if request.method == 'POST':
        action = request.POST.get('action')
        user_ids = request.POST.getlist('user_ids')
        
        if action == 'delete' and user_ids:
            try:
                from django.db.models import Q
                User.objects.filter(id__in=user_ids).delete()
                message = f"Usunięto {len(user_ids)} użytkownika(ów)"
                users = User.objects.all()
                return render(request, 'pages/admin.html', {'users': users, 'message': message})
            except Exception as e:
                error_message = f"Błąd przy usuwaniu użytkowników: {str(e)}"
                users = User.objects.all()
                return render(request, 'pages/admin.html', {'users': users, 'error': error_message})
    
    users = User.objects.all()
    return render(request, 'pages/admin.html', {'users': users})


def logout_view(request):
    """Handle user logout."""
    from django.contrib.auth import logout
    logout(request)
    # Redirect to configured logout redirect (reuses admin_black signin)
    try:
        return redirect(settings.LOGOUT_REDIRECT_URL)
    except Exception:
        return render(request, 'pages/dashboard.html', {'message': 'Zostałeś wylogowany'})


def redirect_to_admin_signin(request):
    """Redirect named 'login' URL to the existing admin_black signin page."""
    return redirect('/accounts/auth-signin/')


@csrf_exempt
def reset_user_password(request):
    """Admin function to reset a user's password."""
    if not request.user.is_authenticated or request.user.username != 'admin':
        return JsonResponse({'status': 'error', 'message': 'Brak dostępu.'})
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            new_password = data.get('new_password')
            confirm_password = data.get('confirm_password')
            
            # Validate passwords match
            if new_password != confirm_password:
                return JsonResponse({'status': 'error', 'message': 'Hasła się nie zgadzają.'})
            
            # Validate password length
            if len(new_password) < 8:
                return JsonResponse({'status': 'error', 'message': 'Hasło musi mieć co najmniej 8 znaków.'})
            
            # Get the user and reset password
            user = User.objects.get(id=user_id)
            user.set_password(new_password)
            user.save()
            
            return JsonResponse({'status': 'success', 'message': f'Hasło użytkownika {user.username} zostało zmienione.'})
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Użytkownik nie znaleziony.'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Błąd: {str(e)}'})
    
    return JsonResponse({'status': 'error', 'message': 'Nieprawidłowa metoda żądania.'})


def propose_movie(request):
    """Allow logged-in users to propose a movie."""
    if not request.user.is_authenticated:
        return redirect('auth_signin')
    
    if request.method == 'POST':
        form = MovieProposalForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data['title']
            imdb_id = form.cleaned_data.get('imdb_id')
            
            # Check if movie with this title already exists
            existing = MovieProposal.objects.filter(title__iexact=title).first()
            if existing:
                message = f"Film '{title}' został już zaproponowany przez {existing.proposer.username}. Zagłosuj na niego zamiast tego!"
                return render(request, 'pages/propose.html', {'form': form, 'message': message})
            
            # Create new proposal
            MovieProposal.objects.create(title=title, imdb_id=imdb_id, proposer=request.user)
            message = f"Film '{title}' został zaproponowany!"
            
            log_action(request, 'proposal_create', proposal_title=title)


            return render(request, 'pages/propose.html', {'form': MovieProposalForm(), 'message': message, 'success': True})
    else:
        form = MovieProposalForm()
    
    return render(request, 'pages/propose.html', {'form': form})


def search_imdb(request):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Musisz się zalogować.'})
    
    query = request.GET.get('q', '').strip()
    if not query or len(query) < 2:
        return JsonResponse({'status': 'error', 'message': 'Wpisz co najmniej 2 znaki.'})
    
    try:
        # Exact URL as in your working example
        api_url = "https://api.imdbapi.dev/search/titles"

        params = {
            'query': query
        }

        response = requests.get(api_url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()

        # imdbapi.dev: titles are in "titles"
        titles = data.get('titles', [])
        if not titles:
            return JsonResponse({
                'status': 'error',
                'message': 'Nie znaleziono filmów o takim tytule.'
            })

        results = []
        for m in titles[:10]:
            title = m.get('primaryTitle') or m.get('originalTitle') or ''
            year = m.get('startYear') or ''
            imdbid = m.get('id') or ''
            poster = ''
            img = m.get('primaryImage') or {}
            if isinstance(img, dict):
                poster = img.get('url', '')

            results.append({
                'title': title,
                'year': year,
                'imdbid': imdbid,
                'poster': poster,
            })

        if not results:
            return JsonResponse({
                'status': 'error',
                'message': 'Nie znaleziono filmów o takim tytule.'
            })

        return JsonResponse({
            'status': 'success',
            'results': results
        })
    except requests.exceptions.RequestException as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Błąd komunikacji z IMDb: {str(e)}'
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': f'Błąd: {str(e)}'
        })



from django.db.models import Count
import requests

def vote_page(request):
    """Show all movie proposals sorted by votes."""
    from django.db.models import Count
    import requests
    
    proposals = MovieProposal.objects.annotate(
        vote_count=Count('proposal_votes')
    ).order_by('-vote_count', '-created_at')
    
    user_votes = set()
    if request.user.is_authenticated:
        user_votes = set(
            ProposalVote.objects.filter(voter=request.user).values_list('proposal_id', flat=True)
        )
    
    proposals_with_votes = []
    for p in proposals:
        # Get voter usernames
        voters = ProposalVote.objects.filter(proposal=p).values_list('voter__username', flat=True)
        voter_names = list(voters)  # ['user1', 'user2', ...]
        
        imdb_data = {}
        if p.imdb_id:
            try:
                url = f"https://api.imdbapi.dev/titles/{p.imdb_id}"
                resp = requests.get(url, timeout=5)
                if resp.status_code == 200:
                    payload = resp.json()
                    d = payload.get('title', {}) or payload
                    img = d.get('primaryImage') or {}
                    rating = d.get('rating') or {}
                    
                    imdb_data = {
                        "title": d.get('primaryTitle') or d.get('originalTitle') or "",
                        "year": d.get('startYear') or "",
                        "plot": (d.get('plotOutline', {}).get('text') if isinstance(d.get('plotOutline'), dict) else ""),
                        "runtime": d.get('runtimeSeconds'),
                        "genres": d.get('genres') or [],
                        "poster": img.get('url') if isinstance(img, dict) else "",
                        "imdb_rating": rating.get('aggregateRating'),
                        "imdb_votes": rating.get('voteCount'),
                    }
            except Exception:
                pass

        proposals_with_votes.append({
            'id': p.id,
            'title': p.title,
            'proposer': p.proposer.username,
            'vote_count': p.vote_count,
            'created_at': p.created_at,
            'user_voted': p.id in user_votes,
            'imdb_id': p.imdb_id,
            'imdb': imdb_data,
            'voters': voter_names,  # Add this line
        })
    
    return render(request, 'pages/vote.html', {
        'proposals': proposals_with_votes,
        'is_authenticated': request.user.is_authenticated,
        'is_admin': request.user.is_authenticated and request.user.username == 'admin'
    })


def vote_proposal(request, proposal_id):
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Musisz się zalogować, aby głosować.'})
    
    try:
        proposal = MovieProposal.objects.get(id=proposal_id)
        vote = ProposalVote.objects.filter(proposal=proposal, voter=request.user).first()
        
        if vote:
            vote.delete()
            action = 'vote_remove'
            log_action(request, 'vote_remove', proposal.id, proposal.title)
        else:
            ProposalVote.objects.create(proposal=proposal, voter=request.user)
            action = 'vote_add'
            log_action(request, 'vote_add', proposal.id, proposal.title)
        
        vote_count = ProposalVote.objects.filter(proposal=proposal).count()
        return JsonResponse({
            'status': 'success',
            'message': f'Głos {action}.',
            'vote_count': vote_count,
            'action': action
        })
    except MovieProposal.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Propozycja nie znaleziona.'})

@csrf_exempt
def delete_proposal(request, proposal_id):
    if not request.user.is_authenticated or request.user.username != 'admin':
        return JsonResponse({'status': 'error', 'message': 'Brak dostępu.'})
    
    try:
        proposal = MovieProposal.objects.get(id=proposal_id)
        title = proposal.title
        proposal.delete()
        log_action(request, 'proposal_delete', proposal_id, title)
        return JsonResponse({'status': 'success', 'message': f'Propozycja "{title}" została usunięta.'})
    except MovieProposal.DoesNotExist:
        return JsonResponse({'status': 'success', 'message': 'Propozycja już nie istnieje.'})

    

@require_POST
def mark_watched(request, proposal_id):
    """Admin function: mark movie from proposal as watched in CSV; if not found, add new row."""
    if not request.user.is_authenticated or request.user.username != 'admin':
        return JsonResponse({'status': 'error', 'message': 'Brak dostępu.'})

    try:
        proposal = MovieProposal.objects.get(id=proposal_id)
    except MovieProposal.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Propozycja nie znaleziona.'})

    title = (proposal.title or '').strip()
    title_lower = title.lower()

    csv_path = os.path.join(settings.MEDIA_ROOT, 'data.csv')
    if not os.path.exists(csv_path):
        return JsonResponse({'status': 'error', 'message': 'Plik CSV nie istnieje.'})

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)

        if not rows:
            header = ["Number", "Title", "Year", "Duration", "Age Rating", "Rating",
                      "Votes", "Metascore", "Description", "Watched", "Skipped",
                      "Series", "Poster URL"]
            data_rows = []
        else:
            header = rows[0]
            data_rows = rows[1:]

        watched_idx = 9
        skipped_idx = 10

        updated = False
        max_number = 0

        # szukaj istniejącego filmu
        for row in data_rows:
            if len(row) == 0:
                continue

            try:
                num = int(row[0])
                if num > max_number:
                    max_number = num
            except (ValueError, IndexError):
                pass

            if len(row) <= max(watched_idx, skipped_idx):
                continue

            row_title = (row[1] or '').strip().lower()

            if row_title == title_lower:
                row[watched_idx] = 'TRUE'
                if len(row) > skipped_idx:
                    row[skipped_idx] = 'FALSE'
                updated = True
                break

        delete_proposal = False  # flaga czy usuwać propozycję

        if not updated:
            # DODAJ NOWY wiersz do CSV
            new_number = max_number + 1
            year = ''
            description = ''
            duration = ''

            new_row = [
                str(new_number), title, year, duration, '-', '-', '-', '-', description,
                'TRUE', 'FALSE', 'FALSE', ''
            ]
            data_rows.append(new_row)
            delete_proposal = True  # usuń propozycję po dodaniu nowego filmu
        # else: film już istnieje w CSV - tylko zaktualizowano Watched, propozycja zostaje

        # zapisz CSV
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(data_rows)

        # usuń propozycję TYLKO gdy dodaliśmy nowy film do CSV
        if delete_proposal:
            proposal.delete()
            msg = f'Film "{title}" dodany do CSV i oznaczony jako obejrzany. Usunięto z propozycji.'
        else:
            msg = f'Film "{title}" oznaczony jako obejrzany w CSV.'
        log_action(request, 'movie_mark_watched', proposal_id, proposal.title, 
           f"Updated: {updated}, Added new: {not updated}")
        return JsonResponse({'status': 'success', 'message': msg})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Błąd: {str(e)}'})

def admin_logs(request):
    """Admin page to view all logs."""
    if not request.user.is_authenticated or request.user.username != 'admin':
        return redirect('vote_page')  # lub dashboard
    
    logs = LogEntry.objects.all()[:1000]  # ostatnie 1000 wpisów
    
    return render(request, 'pages/admin_logs.html', {
        'logs': logs,
        'log_count': LogEntry.objects.count()
    })
