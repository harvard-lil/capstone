import geoip2.database

from django.conf import settings


_geoip_reader = None


def geolocate(ip):
    if not settings.GEOLOCATION_FEATURE:
        raise Exception("Cannot geolocate with GEOLOCATION_FEATURE=False")
    global _geoip_reader
    if not _geoip_reader:
        _geoip_reader = geoip2.database.Reader(settings.GEOIP_PATH)
    return _geoip_reader.city(ip)
