# core/middleware/db_wakeup.py
import time
from django.db import connection
from django.db.utils import OperationalError
from django.shortcuts import render

class DatabaseWakeUpMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
        except OperationalError:
            # First failure → DB is sleeping
            time.sleep(1)  # trigger wake-up

            return render(request, "db_waking_up.html", status=503)

        return self.get_response(request)
