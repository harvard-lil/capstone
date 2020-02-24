from pathlib import Path

import geoip2.database
from django.conf import settings


if settings.GEOLOCATION_FEATURE:
    geoip_reader = geoip2.database.Reader(str(Path(settings.BASE_DIR, 'test_data/GeoLite2-City.mmdb')))

def geolocate(ip):
    if not settings.GEOLOCATION_FEATURE:
        raise Exception("Cannot geolocate with GEOLOCATION_FEATURE=False")
    return geoip_reader.city(ip)
