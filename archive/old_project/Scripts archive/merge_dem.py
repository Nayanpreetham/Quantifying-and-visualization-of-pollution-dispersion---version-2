import rasterio
from rasterio.merge import merge
import glob

# Find ALL tif files inside subfolders
files = [f for f in glob.glob("**/*.tif", recursive=True) if 'india_dem.tif' not in f]

print(f"Found {len(files)} .tif files")

# Open all datasets
datasets = [rasterio.open(f) for f in files]

# Merge
mosaic, out_trans = merge(datasets)

# Metadata
out_meta = datasets[0].meta.copy()
out_meta.update({
    "height": mosaic.shape[1],
    "width": mosaic.shape[2],
    "transform": out_trans
})

# Save merged file
with rasterio.open("india_dem.tif", "w", **out_meta) as dest:
    dest.write(mosaic)

print("Merged DEM created: india_dem.tif")