from django.shortcuts import render
from django.http import JsonResponse
import requests
import csv
import os
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

# Define the path for the CSV file
CSV_FILE_PATH = "data.csv"

def index(request):
    csv_data = load_csv_from_file()
    filter_by = request.GET.get('filter', 'not_watched')
    sort_by = request.GET.get('sort')

    if csv_data and len(csv_data) > 1:
        header, rows = csv_data[0], csv_data[1:]
        display_rows = rows

        if filter_by == 'watched':
            display_rows = [row for row in rows if len(row) > 10 and row[9] == 'TRUE']
        elif filter_by == 'skipped':
            display_rows = [row for row in rows if len(row) > 10 and row[10] == 'TRUE']
        elif filter_by == 'not_watched':
            display_rows = [row for row in rows if len(row) > 10 and row[9] != 'TRUE' and row[10] != 'TRUE']

        if not sort_by:
            sort_by = 'desc' if filter_by == 'not_watched' else 'asc'

        if sort_by == 'asc':
            display_rows = sorted(display_rows, key=lambda x: int(x[0]))
        elif sort_by == 'desc':
            display_rows = sorted(display_rows, key=lambda x: int(x[0]), reverse=True)

        csv_data = [header] + display_rows

    return render(request, 'pages/dashboard.html', {'csv_data': csv_data})






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
                return JsonResponse({"status": "error", "message": f"Entry with ID {entry_id} not found."})

            # Save the updated data back to the file
            save_csv_to_file([header] + rows)
            print("All good!!!")
            return JsonResponse({"status": "success", "message": f"Entry {entry_id} updated successfully!"})
        except Exception as e:
            print("Issue!!")
            return JsonResponse({"status": "error", "message": str(e)})
    return JsonResponse({"status": "error", "message": "Invalid request method."})