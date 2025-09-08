# In healthcare_project/wsgi.py

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'healthcare_project.settings')

application = get_wsgi_application()

# ==========================================================
# ------------ THE FINAL, CRUCIAL FIX IS HERE ------------
# Vercel's Python runtime specifically looks for a variable named 'app'.
# This line creates it.
# ==========================================================
app = application