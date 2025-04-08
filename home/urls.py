from django.urls import path
from home.views import index, refresh_csv_data, update_entry

urlpatterns = [
    path('', index, name='index'),
    path('refresh-data/', refresh_csv_data, name='refresh_data'),
    path('update-entry/', update_entry, name='update_entry'),
]
