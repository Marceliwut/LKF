from django.urls import path
from home.views import index, refresh_csv_data, update_entry, backup_csv, file_explorer, restore_backup, recommend_next_watch, update_posters, find_next_shortest_movie
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', index, name='index'),
    path('refresh-data/', refresh_csv_data, name='refresh_data'),
    path('update_entry/', update_entry, name='update_entry'),
    path("backup_csv/", backup_csv, name="backup_csv"),
    path('file_explorer/', file_explorer, name='file_explorer'),
    path('restore_backup/', restore_backup, name='restore_backup'),
    path('recommend_next_watch/', recommend_next_watch, name='recommend_next_watch'),
    path('update_posters/', update_posters, name='update_posters'),
    path('find_next_shortest_movie/', find_next_shortest_movie, name='find_next_shortest_movie'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)