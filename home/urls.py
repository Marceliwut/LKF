from django.urls import path
from home.views import index, refresh_csv_data, update_entry, backup_csv

urlpatterns = [
    path('', index, name='index'),
    path('refresh-data/', refresh_csv_data, name='refresh_data'),
    path('update-entry/', update_entry, name='update_entry'),
    path("backup_csv/", backup_csv, name="backup_csv"),
]
