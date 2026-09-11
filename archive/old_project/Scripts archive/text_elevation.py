import rasterio

datset = rasterio.open('india_dem.tif')

def get_elevation(lat, lon):
    row, col = datset.index(lon, lat)
    elevation = datset.read(1)[row, col]
    return elevation

lat = 28.6139
lon = 77.2090
elevation = get_elevation(lat, lon )
print(f"Elevation at ({lat}, {lon}): {elevation} meters")