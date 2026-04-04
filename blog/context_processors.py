from .models import SiteConfiguration

def site_settings(request):
    config = SiteConfiguration.objects.first()
    return {
        'site_config': config
    }
