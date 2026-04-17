from .models import GymSetting, SiteConfiguration

def site_settings(request):
    """Retorna as configurações gerais do site (SEO, Links, etc)"""
    config = SiteConfiguration.objects.first()
    return {'site_config': config}

def gym_branding(request):
    try:
        branding = GymSetting.objects.first()
    except:
        branding = None
        
    return {
        'gym_settings': branding
    }
