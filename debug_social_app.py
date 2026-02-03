import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'healthcare_project.settings')
django.setup()

from allauth.socialaccount.models import SocialApp
from django.contrib.sites.models import Site

def check_apps():
    print(f"Current Site ID: {django.conf.settings.SITE_ID}")
    try:
        current_site = Site.objects.get(id=django.conf.settings.SITE_ID)
        print(f"Current Site Domain: {current_site.domain}")
    except Site.DoesNotExist:
        print("CRITICAL: Current Site ID does not exist in DB!")

    apps = SocialApp.objects.filter(provider='google')
    if not apps.exists():
        print("ERROR: No SocialApp found for provider 'google'.")
        print("ACTION REQUIRED: You must go to Django Admin > Social Applications and add a Google app.")
    else:
        for app in apps:
            print(f"Found App: {app.name} (Client ID: {app.client_id})")
            sites = app.sites.all()
            print(f"  - Linked Sites: {[s.domain for s in sites]}")
            if current_site in sites:
                print("  - SUCCESS: App is correctly linked to current site.")
            else:
                print("  - ERROR: App is NOT linked to current site. Please edit the app in Admin and select the site.")
                # Auto-fix attempt
                print("  - ATTEMPTING FIX: Linking app to current site...")
                app.sites.add(current_site)
                app.save()
                print("  - FIXED: App linked.")

if __name__ == '__main__':
    check_apps()
