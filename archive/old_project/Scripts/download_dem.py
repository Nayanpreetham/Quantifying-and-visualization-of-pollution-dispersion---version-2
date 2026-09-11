import elevation

# India bounding box
west, south, east, north = 68, 6, 97, 35

# Grid split: 4 rows × 8 columns = 32 parts
rows = 4
cols = 8

lat_step = (north - south) / rows
lon_step = (east - west) / cols

part = 0

for i in range(rows):
    for j in range(cols):
        w = west + j * lon_step
        e = west + (j + 1) * lon_step
        s = south + i * lat_step
        n = south + (i + 1) * lat_step

        bounds = (w, s, e, n)

        print(f"Downloading part {part} → {bounds}")
        
        try:
            elevation.clip(bounds=bounds, output=f'dem_part_{part}.tif')
        except Exception as e:
            print(f"Failed part {part}: {e}")

        part += 1

print("All parts attempted")