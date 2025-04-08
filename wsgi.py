import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings')  # Replace 'settings' with your settings module if different

application = get_wsgi_application()