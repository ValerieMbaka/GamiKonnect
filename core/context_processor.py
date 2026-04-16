from django.conf import settings
from .models import SiteStyle, ProjectDetail


def site_style(request):
    style = SiteStyle.get_active()
    return {"site_style": style.as_dict() if style else {}}


def firebase_config(request):
    # Provide client-side Firebase config for templates if available in settings
    cfg = getattr(settings, "FIREBASE_CLIENT_CONFIG", None)
    return {"firebase_config": cfg or {}}


def global_site_context(request):
    # Automatically injects global site configuration across all pages
    project_detail = ProjectDetail.objects.filter(is_active=True).first()
    
    # Dynamically determine site_url from the current request
    # This ensures that whether on localhost or production, links in templates are correct
    site_url = request.build_absolute_uri('/').rstrip('/')
    
    return {
        'project_detail': project_detail,
        'site_url': site_url,
    }