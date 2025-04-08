from django.urls import path
from home.views import index, refresh_csv_data, update_entry, backup_csv, file_explorer, restore_backup, recommend_next_watch
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', index, name='index'),
    path('refresh-data/', refresh_csv_data, name='refresh_data'),
    path('update-entry/', update_entry, name='update_entry'),
    path("backup_csv/", backup_csv, name="backup_csv"),
    path('file_explorer/', file_explorer, name='file_explorer'),
    path('restore_backup/', restore_backup, name='restore_backup'),
    path('recommend_next_watch/', recommend_next_watch, name='recommend_next_watch'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)