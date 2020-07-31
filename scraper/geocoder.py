import googlemaps
import json

API_KEY = "AIzaSyA-pfgrotEjJLMzGhY50Xky8_c5DZO3iCs"

def get_coordinates(address_str):
    gmaps = googlemaps.Client(key=API_KEY)
    geocode_result = gmaps.geocode(address_str)
    if len(geocode_result) == 0:
        return {'lat': None, 'lng': None}
    result_geom = geocode_result[0]['geometry']['location']
    return result_geom
