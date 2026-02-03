import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'healthcare_project.settings')
django.setup()

from django.contrib.sites.models import Site

def fix_site():
    # Get the site with ID 1 (default)
    try:
        site = Site.objects.get(id=1)
        print(f"Current Site: {site.domain} ({site.name})")
        
        # Update to local development domain
        site.domain = '127.0.0.1:8000'
        site.name = 'Healthcare Local'
        site.save()
        print(f"Updated Site to: {site.domain} ({site.name})")
        print("SUCCESS: Site domain fixed. Ensure your Google Cloud Authorized Redirect URI matches: http://127.0.0.1:8000/accounts/google/login/callback/")
    except Site.DoesNotExist:
        print("Site with ID 1 does not exist. Creating it...")
        Site.objects.create(id=1, domain='127.0.0.1:8000', name='Healthcare Local')
        print("SUCCESS: Created Site ID 1.")

if __name__ == '__main__':
    fix_site()
