from django.urls import path
from home.views import *
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', index, name='index'),
    path('refresh-data/', refresh_csv_data, name='refresh_data'),
    path('register/', register_view, name='register'),
    path('update_entry/', update_entry, name='update_entry'),
    path("backup_csv/", backup_csv, name="backup_csv"),
    path('file_explorer/', file_explorer, name='file_explorer'),
    path('restore_backup/', restore_backup, name='restore_backup'),
    path('recommend_next_watch/', recommend_next_watch, name='recommend_next_watch'),
    path('update_posters/', update_posters, name='update_posters'),
    path('find_next_shortest_movie/', find_next_shortest_movie, name='find_next_shortest_movie'),
    path('login/', redirect_to_admin_signin, name='login'),
    path('logout/', logout_view, name='logout'),
    path('admin/', admin_view, name='admin'),
    path('reset_user_password/', reset_user_password, name='reset_user_password'),
    path('propose/', propose_movie, name='propose'),
    path('search_imdb/', search_imdb, name='search_imdb'),
    path('vote/', vote_page, name='vote'),
    path('vote/<int:proposal_id>/', vote_proposal, name='vote_proposal'),
    path('delete_proposal/<int:proposal_id>/', delete_proposal, name='delete_proposal'),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)