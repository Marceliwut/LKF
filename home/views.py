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
from .forms import CustomLoginForm, CustomSignupForm, AdminResetPasswordForm, ChangePasswordForm, MovieProposalForm
from .models import MovieProposal, ProposalVote, LogEntry, MovieRating
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
    """Redirect to vote page. Home page now shows movie proposals to vote on."""
    return redirect('vote')

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
        
        elif action == 'extend_limit' and user_ids:
            try:
                additional_limit = int(request.POST.get('additional_limit', 0))
                if additional_limit <= 0:
                    raise ValueError("Limit musi być większy od 0")
                
                from .models import UserProposalLimit
                count = 0
                for user_id in user_ids:
                    user = User.objects.get(id=user_id)
                    user_limit, created = UserProposalLimit.objects.get_or_create(user=user)
                    user_limit.limit += additional_limit
                    user_limit.save()
                    log_action(request, 'extend_limit', details=f'Rozszerzono limit propozycji dla użytkownika {user.username} o {additional_limit}. Nowy limit: {user_limit.limit}')
                    count += 1
                
                message = f"Rozszerzono limit propozycji dla {count} użytkownika(ów)"
                users = User.objects.all()
                return render(request, 'pages/admin.html', {'users': users, 'message': message})
            except Exception as e:
                error_message = f"Błąd przy rozszerzaniu limitu: {str(e)}"
                users = User.objects.all()
                return render(request, 'pages/admin.html', {'users': users, 'error': error_message})
    
    users = User.objects.all()
    from .models import UserProposalLimit
    # Attach proposal limit info to each user
    for user in users:
        try:
            user.proposal_limit_value = UserProposalLimit.objects.get(user=user).limit
        except UserProposalLimit.DoesNotExist:
            user.proposal_limit_value = 10  # Default limit
        except Exception:
            user.proposal_limit_value = 10  # Default limit in case of any database error
    
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


def change_password(request):
    """Allow users to change their own password."""
    if not request.user.is_authenticated:
        return redirect('auth_signin')
    
    if request.method == 'POST':
        form = ChangePasswordForm(request.POST)
        if form.is_valid():
            user = request.user
            current_password = form.cleaned_data.get('current_password')
            new_password = form.cleaned_data.get('new_password')
            
            # Verify current password
            if not user.check_password(current_password):
                form.add_error('current_password', 'Bieżące hasło jest niepoprawne.')
                return render(request, 'pages/change_password.html', {'form': form})
            
            # Set the new password
            user.set_password(new_password)
            user.save()
            
            # Log the action
            log_action(request, 'password_changed', details='Użytkownik zmienił swoje hasło')
            
            # Show success message with countdown and redirect to login
            return render(request, 'pages/change_password.html', {
                'form': ChangePasswordForm(),
                'success': True,
                'message': 'Hasło zostało pomyślnie zmienione. Przesyłanie na stronę logowania...',
                'show_countdown': True
            })
    else:
        form = ChangePasswordForm()
    
    return render(request, 'pages/change_password.html', {'form': form})


def propose_movie(request):
    """Allow logged-in users to propose a movie. Max 10 active proposals per user (configurable by admin)."""
    if not request.user.is_authenticated:
        return redirect('auth_signin')
    
    # Get user's proposal limit
    from .models import UserProposalLimit
    user_limit = 10  # Default limit
    try:
        user_limit = UserProposalLimit.objects.get(user=request.user).limit
    except UserProposalLimit.DoesNotExist:
        user_limit = 10  # Default limit
    except Exception:
        user_limit = 10  # Default limit in case of database error
    
    if request.method == 'POST':
        form = MovieProposalForm(request.POST)
        if form.is_valid():
            title = form.cleaned_data['title']
            imdb_id = form.cleaned_data.get('imdb_id')
            
            # Check user's active proposal count
            user_proposal_count = MovieProposal.objects.filter(proposer=request.user).count()
            if user_proposal_count >= user_limit:
                message = f"Osiągnąłeś maksymalną liczbę aktywnych propozycji ({user_limit}). Usuń lub czekaj aż jedna z Twoich propozycji będzie oznaczona jako oglądnięta."
                return render(request, 'pages/propose.html', {'form': form, 'message': message, 'proposal_limit': user_limit})
            
            # Check if movie with this title already exists
            existing = MovieProposal.objects.filter(title__iexact=title).first()
            if existing:
                message = f"Film '{title}' został już zaproponowany przez {existing.proposer.username}. Zagłosuj na niego zamiast tego!"
                return render(request, 'pages/propose.html', {'form': form, 'message': message, 'proposal_limit': user_limit})
            
            # Create new proposal
            MovieProposal.objects.create(title=title, imdb_id=imdb_id, proposer=request.user)
            message = f"Film '{title}' został zaproponowany! (Aktywne: {user_proposal_count + 1}/{user_limit})"
            
            log_action(request, 'proposal_create', proposal_title=title)

            return render(request, 'pages/propose.html', {'form': MovieProposalForm(), 'message': message, 'success': True, 'proposal_limit': user_limit})
    else:
        form = MovieProposalForm()
    
    # Get user's current proposal count
    user_proposal_count = MovieProposal.objects.filter(proposer=request.user).count() if request.user.is_authenticated else 0
    
    return render(request, 'pages/propose.html', {'form': form, 'proposal_count': user_proposal_count, 'proposal_limit': user_limit})


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
    """Show all movie proposals sorted by votes, or watched movies if filter=watched."""
    from django.db.models import Count
    import requests
    
    filter_type = request.GET.get('filter', 'proposals')
    
    # If filter is 'watched', show watched movies from CSV
    if filter_type == 'watched':
        csv_file_path = os.path.join(settings.MEDIA_ROOT, 'data.csv')
        watched_movies = []
        
        if os.path.exists(csv_file_path):
            with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                rows = list(reader)
                
                if len(rows) > 1:
                    header, data = rows[0], rows[1:]
                    # Filter for watched movies
                    watched_data = [row for row in data if len(row) > 9 and row[9] == 'TRUE']
                    # Sort by number descending (most recent first)
                    watched_data = sorted(watched_data, key=lambda x: int(x[0]) if x[0].isdigit() else 0, reverse=True)
                    
                    # Enhance watched movies with poster data
                    for movie in watched_data:
                        movie_dict = {
                            'number': movie[0] if len(movie) > 0 else '',
                            'title': movie[1] if len(movie) > 1 else '',
                            'year': movie[2] if len(movie) > 2 else '',
                            'duration': movie[3] if len(movie) > 3 else '',
                            'age_rating': movie[4] if len(movie) > 4 else '',
                            'rating': movie[5] if len(movie) > 5 else '',
                            'votes': movie[6] if len(movie) > 6 else '',
                            'metascore': movie[7] if len(movie) > 7 else '',
                            'description': movie[8] if len(movie) > 8 else '',
                            'poster_url': movie[12] if len(movie) > 12 else '',
                        }
                        watched_movies.append(movie_dict)
        
        return render(request, 'pages/vote.html', {
            'proposals': None,
            'watched_movies': watched_movies,
            'is_authenticated': request.user.is_authenticated,
            'is_admin': request.user.is_authenticated and request.user.username == 'admin',
            'filter_type': 'watched'
        })
    
    # Default: show proposals to vote on
    from django.utils import timezone
    from datetime import timedelta
    
    proposals = MovieProposal.objects.annotate(
        vote_count=Count('proposal_votes')
    ).order_by('-vote_count', '-created_at')
    
    user_votes = set()
    if request.user.is_authenticated:
        user_votes = set(
            ProposalVote.objects.filter(voter=request.user).values_list('proposal_id', flat=True)
        )
    
    proposals_with_votes = []
    proposals_to_cache = []  # Track proposals that need fresh data
    
    # Pre-fetch all voter data for all proposals at once (avoid N+1 queries)
    # Get all votes with valid voters for all proposals
    all_votes = ProposalVote.objects.filter(
        proposal_id__in=[p.id for p in proposals],
        voter__isnull=False
    ).select_related('voter')
    
    # Group votes by proposal ID for quick lookup
    votes_by_proposal = {}
    for vote in all_votes:
        if vote.proposal_id not in votes_by_proposal:
            votes_by_proposal[vote.proposal_id] = []
        votes_by_proposal[vote.proposal_id].append(vote.voter.username)
    
    for p in proposals:
        # Get voter usernames from our pre-fetched data (no new queries)
        voter_names = votes_by_proposal.get(p.id, [])
        
        imdb_data = {}
        
        # Check if we have cached IMDb data (cache for 24 hours)
        cache_expired = not p.cached_at or (timezone.now() - p.cached_at > timedelta(hours=24))
        
        if p.imdb_id and p.cached_imdb_data and not cache_expired:
            # Use cached data
            imdb_data = p.cached_imdb_data
        elif p.imdb_id and cache_expired:
            # Data expired or missing - fetch fresh (but don't block page load)
            try:
                url = f"https://api.imdbapi.dev/titles/{p.imdb_id}"
                resp = requests.get(url, timeout=3)  # Reduced timeout
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
                    
                    # Cache the data
                    p.cached_imdb_data = imdb_data
                    p.cached_at = timezone.now()
                    proposals_to_cache.append(p)
            except Exception as e:
                # If API call fails, use old cached data if available
                if p.cached_imdb_data:
                    imdb_data = p.cached_imdb_data
                print(f"Error fetching IMDb data for {p.imdb_id}: {e}")

        proposals_with_votes.append({
            'id': p.id,
            'title': p.title,
            'proposer': p.proposer.username,
            'proposer_id': p.proposer.id,
            'vote_count': p.vote_count,
            'created_at': p.created_at,
            'user_voted': p.id in user_votes,
            'is_proposer': request.user.is_authenticated and request.user == p.proposer,
            'imdb_id': p.imdb_id,
            'imdb': imdb_data,
            'voters': voter_names,
        })
    
    # Bulk update cached proposals (efficient batch operation)
    if proposals_to_cache:
        MovieProposal.objects.bulk_update(proposals_to_cache, ['cached_imdb_data', 'cached_at'], batch_size=100)
    
    return render(request, 'pages/vote.html', {
        'proposals': proposals_with_votes,
        'watched_movies': None,
        'is_authenticated': request.user.is_authenticated,
        'is_admin': request.user.is_authenticated and request.user.username == 'admin',
        'filter_type': 'proposals'
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
    """Delete a proposal. Only admin or the proposal creator can delete it."""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Brak dostępu.'})
    
    try:
        proposal = MovieProposal.objects.get(id=proposal_id)
        
        # Check if user is admin or the proposer
        if request.user.username != 'admin' and request.user != proposal.proposer:
            return JsonResponse({'status': 'error', 'message': 'Możesz usunąć tylko swoje propozycje.'})
        
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
            # Film już istnieje w CSV - też usuń propozycję żeby zwolnić slot użytkownikowi
            proposal.delete()
            msg = f'Film "{title}" oznaczony jako obejrzany w CSV. Propozycja usunięta.'
        log_action(request, 'movie_mark_watched', proposal_id, proposal.title, 
           f"Updated: {updated}, Added new: {not updated}")
        return JsonResponse({'status': 'success', 'message': msg})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Błąd: {str(e)}'})



@csrf_exempt
def rate_movie(request):
    """Handle movie rating submission."""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Musisz się zalogować.'})
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            movie_title = data.get('movie_title')
            rating = data.get('rating')
            
            if not movie_title or not rating:
                return JsonResponse({'status': 'error', 'message': 'Brak wymaganych danych.'})
            
            rating = int(rating)
            if rating < 1 or rating > 5:
                return JsonResponse({'status': 'error', 'message': 'Ocena musi być od 1 do 5.'})
            
            # Create or update rating
            from .models import MovieRating
            movie_rating, created = MovieRating.objects.update_or_create(
                movie_title=movie_title,
                user=request.user,
                defaults={'rating': rating}
            )
            
            # Get all ratings for this movie
            all_ratings = MovieRating.objects.filter(movie_title=movie_title).values_list('rating', flat=True)
            avg_rating = sum(all_ratings) / len(all_ratings) if all_ratings else 0
            
            # Get ratings by user
            ratings_by_user = MovieRating.objects.filter(movie_title=movie_title).values('user__username', 'rating').order_by('-created_at')
            
            return JsonResponse({
                'status': 'success',
                'message': 'Ocena zapisana.',
                'average_rating': round(avg_rating * 2) / 2,  # Round to nearest 0.5
                'rating_count': len(all_ratings),
                'ratings_by_user': list(ratings_by_user)
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Błąd: {str(e)}'})
    
    return JsonResponse({'status': 'error', 'message': 'Nieprawidłowa metoda żądania.'})


@csrf_exempt
def get_movie_ratings(request):
    """Get ratings for a specific movie."""
    if request.method == 'GET':
        movie_title = request.GET.get('movie_title')
        
        if not movie_title:
            return JsonResponse({'status': 'error', 'message': 'Brak tytułu filmu.'})
        
        from .models import MovieRating
        all_ratings = MovieRating.objects.filter(movie_title=movie_title).values_list('rating', flat=True)
        avg_rating = sum(all_ratings) / len(all_ratings) if all_ratings else 0
        
        # Get ratings by user
        ratings_by_user = MovieRating.objects.filter(movie_title=movie_title).values('user__username', 'rating').order_by('-created_at')
        
        # Get current user's rating if authenticated
        user_rating = None
        if request.user.is_authenticated:
            rating_obj = MovieRating.objects.filter(movie_title=movie_title, user=request.user).first()
            if rating_obj:
                user_rating = rating_obj.rating
        
        return JsonResponse({
            'status': 'success',
            'average_rating': round(avg_rating * 2) / 2,
            'rating_count': len(all_ratings),
            'user_rating': user_rating,
            'ratings_by_user': list(ratings_by_user)
        })
    
    return JsonResponse({'status': 'error', 'message': 'Nieprawidłowa metoda żądania.'})


@csrf_exempt
def remove_movie_rating(request):
    """Handle movie rating removal."""
    if not request.user.is_authenticated:
        return JsonResponse({'status': 'error', 'message': 'Musisz się zalogować.'})
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            movie_title = data.get('movie_title')
            
            if not movie_title:
                return JsonResponse({'status': 'error', 'message': 'Brak tytułu filmu.'})
            
            # Delete user's rating
            from .models import MovieRating
            MovieRating.objects.filter(movie_title=movie_title, user=request.user).delete()
            
            # Get remaining ratings for this movie
            all_ratings = MovieRating.objects.filter(movie_title=movie_title).values_list('rating', flat=True)
            avg_rating = sum(all_ratings) / len(all_ratings) if all_ratings else 0
            
            # Get ratings by user
            ratings_by_user = MovieRating.objects.filter(movie_title=movie_title).values('user__username', 'rating').order_by('-created_at')
            
            return JsonResponse({
                'status': 'success',
                'message': 'Ocena usunięta.',
                'average_rating': round(avg_rating * 2) / 2 if all_ratings else 0,
                'rating_count': len(all_ratings),
                'ratings_by_user': list(ratings_by_user)
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Błąd: {str(e)}'})
    
    return JsonResponse({'status': 'error', 'message': 'Nieprawidłowa metoda żądania.'})


def admin_logs(request):
    """Admin page to view all logs."""
    if not request.user.is_authenticated or request.user.username != 'admin':
        return redirect('vote_page')  # lub dashboard
    
    logs = LogEntry.objects.all()[:1000]  # ostatnie 1000 wpisów
    
    return render(request, 'pages/admin_logs.html', {
        'logs': logs,
        'log_count': LogEntry.objects.count()
    })


@csrf_exempt
def remove_watched_movie(request):
    """Admin: remove a movie from the watched list."""
    if not request.user.is_authenticated or request.user.username != 'admin':
        return JsonResponse({'status': 'error', 'message': 'Brak dostępu.'})
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            movie_title = data.get('movie_title')
            
            if not movie_title:
                return JsonResponse({'status': 'error', 'message': 'Brak tytułu filmu.'})
            
            csv_file_path = os.path.join(settings.MEDIA_ROOT, 'data.csv')
            
            if not os.path.exists(csv_file_path):
                return JsonResponse({'status': 'error', 'message': 'Plik CSV nie istnieje.'})
            
            # Read CSV
            with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                rows = list(reader)
            
            if len(rows) < 2:
                return JsonResponse({'status': 'error', 'message': 'Plik CSV jest pusty.'})
            
            # Find and remove the movie by setting watched column (index 9) to FALSE
            header = rows[0]
            data_rows = rows[1:]
            movie_found = False
            
            for row in data_rows:
                if len(row) > 1 and row[1].strip() == movie_title.strip():
                    # Set watched flag (column 9) to FALSE
                    if len(row) > 9:
                        row[9] = 'FALSE'
                    movie_found = True
                    break
            
            if not movie_found:
                return JsonResponse({'status': 'error', 'message': 'Film nie został znaleziony.'})
            
            # Write updated CSV
            with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(header)
                writer.writerows(data_rows)
            
            log_action(request, 'remove_watched_movie', details=f'Usunięto film ze złożonych: {movie_title}')
            
            return JsonResponse({
                'status': 'success',
                'message': f'Film "{movie_title}" został usunięty z listy obejrzanych.'
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Błąd: {str(e)}'})
    
    return JsonResponse({'status': 'error', 'message': 'Nieprawidłowa metoda żądania.'})
