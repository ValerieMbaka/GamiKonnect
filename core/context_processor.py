from .models import SiteStyle

def site_style(request):
    style = SiteStyle.get_active()
    return {"site_style": style.as_dict() if style else {}}
