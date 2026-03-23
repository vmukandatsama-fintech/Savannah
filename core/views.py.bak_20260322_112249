from django.shortcuts import render

# Create your views here.
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.http import HttpResponse


@login_required
def sql_test(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT DB_NAME() AS db_name, @@SERVERNAME AS server_name")
        row = cursor.fetchone()

    return HttpResponse(
        f"Connected successfully. Database: {row[0]} | Server: {row[1]}"
    )