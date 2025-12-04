from django.conf import settings
from .models import SiteStyle

def site_style(request):
    style = SiteStyle.get_active()
    return {"site_style": style.as_dict() if style else {}}

def firebase_config(request):
    # Provide client-side Firebase config for templates if available in settings
    cfg = getattr(settings, "FIREBASE_CLIENT_CONFIG", None)
    return {"firebase_config": cfg or {}}
