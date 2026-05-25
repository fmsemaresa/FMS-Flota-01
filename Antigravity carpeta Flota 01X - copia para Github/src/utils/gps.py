import random

def get_current_gps():
    """Simula y devuelve la geolocalización actual como 'latitud,longitud'.
    Centrado en Santiago de Chile con pequeña variación aleatoria.
    """
    base_lat = -33.4489
    base_lon = -70.6693
    
    # Añadir pequeña variación aleatoria
    lat = base_lat + random.uniform(-0.02, 0.02)
    lon = base_lon + random.uniform(-0.02, 0.02)
    
    return f"{lat:.6f},{lon:.6f}"
