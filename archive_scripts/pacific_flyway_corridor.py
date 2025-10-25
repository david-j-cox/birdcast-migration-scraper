# pip install geopandas shapely pyproj pyogrio tqdm
import geopandas as gpd
from shapely.geometry import LineString
import pandas as pd
import ssl
import urllib.request
from tqdm import tqdm

# Fix SSL certificate verification issues
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# -----------------------------
# 1) Load US counties (Census)
# -----------------------------
# 1:500k generalized counties – fine for selection; swap for TIGER if you want higher detail
print("Downloading US counties data...")
try:
    # Try with SSL context fix
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_context))
    urllib.request.install_opener(opener)
    counties = gpd.read_file(
        "https://www2.census.gov/geo/tiger/GENZ2018/shp/cb_2018_us_county_500k.zip"
    ).to_crs(4326)
    print(f"Successfully loaded {len(counties)} counties from Census Bureau")
except Exception as e:
    print(f"Error downloading Census data: {e}")
    print("Trying alternative approach...")
    # Alternative: use a different source or local file
    counties = gpd.read_file(
        "https://raw.githubusercontent.com/holtzy/The-Python-Graph-Gallery/master/static/data/US-counties.geojson"
    ).to_crs(4326)
    print(f"Successfully loaded {len(counties)} counties from alternative source")

# Keep only states in/near the Pacific corridor to speed things up
print("Filtering to Pacific corridor states...")
keep_statefps = {
    "02",        # Alaska
    "06",        # California
    "41",        # Oregon
    "53",        # Washington
    "16",        # Idaho
    "30",        # Montana
    "56",        # Wyoming
    "08",        # Colorado
    "35",        # New Mexico
    "04",        # Arizona
    "49",        # Utah
    "32",        # Nevada
}
counties = counties[counties["STATEFP"].isin(keep_statefps)].copy()
print(f"Filtered to {len(counties)} counties in Pacific corridor states")

# -----------------------------
# 2) Define the corridor spine
# -----------------------------
# Pacific Flyway route from Alaska to Central America
spine_ll = LineString([
    (-149.900, 61.218),   # Anchorage, Alaska
    (-152.404, 59.964),   # Homer, Alaska
    (-135.338, 57.053),   # Sitka, Alaska
    (-123.116, 49.246),   # Vancouver, BC area
    (-122.676, 45.515),   # Portland, Oregon
    (-123.029, 44.931),   # Salem, Oregon
    (-123.035, 44.564),   # Corvallis, Oregon
    (-124.104, 43.344),   # Coos Bay, Oregon
    (-124.208, 41.759),   # Crescent City, California
    (-123.869, 39.161),   # Ukiah, California
    (-122.419, 37.775),   # San Francisco, California
    (-121.468, 36.951),   # Santa Cruz, California
    (-121.894, 36.610),   # Monterey, California
    (-120.659, 35.295),   # San Luis Obispo, California
    (-119.698, 34.421),   # Santa Barbara, California
    (-118.244, 34.052),   # Los Angeles, California
    (-117.161, 32.715),   # San Diego, California
])

# -------------------------------------------
# 3) Buffer by a fixed kilometer width
# -------------------------------------------
# Project to CONUS Albers (meters) for accurate buffering
print("Projecting coordinates and creating corridor buffer...")
ALBERS = 5070
counties_alb = counties.to_crs(ALBERS)
spine_alb   = gpd.GeoSeries([spine_ll], crs=4326).to_crs(ALBERS).iloc[0]

BUFFER_KM = 150  # << set corridor half-width (wider for Pacific due to mountain ranges)
corridor_poly = spine_alb.buffer(BUFFER_KM * 1000)  # meters
print(f"Created corridor buffer of ±{BUFFER_KM} km")

# -------------------------------------------
# 4) Select counties by centroid-within
# -------------------------------------------
print("Selecting counties within corridor...")
centroids = counties_alb.copy()

# Add progress bar for centroid calculation
tqdm.pandas(desc="Computing centroids")
centroids["centroid"] = counties_alb.geometry.progress_apply(lambda x: x.centroid)

print("Checking which counties fall within corridor...")
# Add progress bar for within check
tqdm.pandas(desc="Checking corridor overlap")
within_mask = centroids["centroid"].progress_apply(lambda x: x.within(corridor_poly))
in_corr = centroids[within_mask].drop(columns="centroid")

# Back to WGS84 for output
in_corr = in_corr.to_crs(4326)
print(f"Found {len(in_corr)} counties within the corridor")

# -------------------------------------------
# 5) Tidy output and save
# -------------------------------------------
state_map = {
    '02':'Alaska','06':'California','41':'Oregon','53':'Washington',
    '16':'Idaho','30':'Montana','56':'Wyoming','08':'Colorado',
    '35':'New Mexico','04':'Arizona','49':'Utah','32':'Nevada'
}

out = in_corr[["STATEFP","COUNTYFP","GEOID","NAME"]].copy()
out["state"]  = out["STATEFP"].map(state_map)
out.rename(columns={"NAME":"county"}, inplace=True)
out = out.sort_values(["state","county"])

# --- Build BirdCast county URLs ---
state_fips_to_abbr = {
    "02":"AK","06":"CA","41":"OR","53":"WA",
    "16":"ID","30":"MT","56":"WY","08":"CO",
    "35":"NM","04":"AZ","49":"UT","32":"NV"
}

out["state_abbr"] = out["STATEFP"].map(state_fips_to_abbr)
out["county_fips3"] = out["COUNTYFP"].astype(str).str.zfill(3)
out["birdcast_url"] = (
    "https://dashboard.birdcast.info/region/US-"
    + out["state_abbr"] + "-" + out["county_fips3"]
)

# Reorder and save
print("Saving results...")
cols = ["state","state_abbr","county","GEOID","county_fips3","birdcast_url"]
out[cols].to_csv("pacific_flyway_corridor_counties_with_urls.csv", index=False)

# Save original format and GeoJSON too
out.to_csv("pacific_flyway_corridor_counties.csv", index=False)
in_corr[["GEOID","geometry"]].to_file("pacific_flyway_corridor_counties.geojson", driver="GeoJSON")
print("Files saved successfully!")

# Print a compact summary
print(f"Corridor width: ±{BUFFER_KM} km; Total counties: {len(out)}\n")
print(out.groupby("state")["county"].count().sort_values(ascending=False))
print("\nSample with BirdCast URLs:")
print(out[cols].head(10))
