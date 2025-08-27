# Your current wsgi.py
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'healthcare_project.settings')

application = get_wsgi_application() # <--- THE VARIABLE IS NAMED 'application'



app = application