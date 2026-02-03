import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'healthcare_project.settings')
django.setup()

from django.urls import reverse
from django.contrib.sites.models import Site

def check_url():
    try:
        # standard allauth pattern for google
        # provider ID is 'google'
        path = reverse('google_callback') 
        print(f"Relative Path found: {path}")
        
        current_site = Site.objects.get(id=settings.SITE_ID)
        domain = current_site.domain
        
        # Determine protocol
        proto = getattr(settings, 'ACCOUNT_DEFAULT_HTTP_PROTOCOL', 'http')
        
        full_url = f"{proto}://{domain}{path}"
        print("----------------------------------------------------------------")
        print("GENERATE AUTHORIZED REDIRECT URI:")
        print(full_url)
        print("----------------------------------------------------------------")
        
        # also print localhost variant
        if '127.0.0.1' in domain:
            localhost_url = full_url.replace('127.0.0.1', 'localhost')
            print("Also add this as a backup (for localhost browsing):")
            print(localhost_url)
            
    except Exception as e:
        print(f"Error calculating URL: {e}")
        # Fallback for manual check
        print("Could not reverse 'google_callback'. Trying 'valid_callback'...")

if __name__ == '__main__':
    check_url()
