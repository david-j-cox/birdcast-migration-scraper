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

# Keep only states in/near the Atlantic corridor to speed things up
print("Filtering to Atlantic corridor states...")
keep_statefps = {
    "09","23","25","33","44","50",        # CT, ME, MA, NH, RI, VT
    "34","36","42","10","24","11",        # NJ, NY, PA, DE, MD, DC
    "51","54","37","45","13","12"         # VA, WV, NC, SC, GA, FL
}
counties = counties[counties["STATEFP"].isin(keep_statefps)].copy()
print(f"Filtered to {len(counties)} counties in Atlantic corridor states")

# -----------------------------
# 2) Define the corridor spine
# -----------------------------
# Add/adjust points to better trace your preferred path
spine_ll = LineString([
    (-73.938, 40.663),   # Brooklyn/NYC
    (-74.172, 40.736),   # Newark
    (-75.165, 39.953),   # Philadelphia
    (-76.612, 39.290),   # Baltimore
    (-77.037, 38.907),   # Washington, DC
    (-77.436, 37.541),   # Richmond
    (-77.460, 36.073),   # Emporia
    (-78.638, 35.780),   # Raleigh
    (-78.939, 33.689),   # Myrtle Beach vicinity
    (-80.000, 32.080),   # Savannah vicinity
    (-81.655, 30.332),   # Jacksonville (Duval)
    (-80.191, 25.762)    # Miami
])

# -------------------------------------------
# 3) Buffer by a fixed kilometer width
# -------------------------------------------
# Project to CONUS Albers (meters) for accurate buffering
print("Projecting coordinates and creating corridor buffer...")
ALBERS = 5070
counties_alb = counties.to_crs(ALBERS)
spine_alb   = gpd.GeoSeries([spine_ll], crs=4326).to_crs(ALBERS).iloc[0]

BUFFER_KM = 120  # << set corridor half-width (e.g., 80, 120, 200)
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
    '09':'Connecticut','23':'Maine','25':'Massachusetts','33':'New Hampshire',
    '44':'Rhode Island','50':'Vermont','34':'New Jersey','36':'New York',
    '42':'Pennsylvania','10':'Delaware','24':'Maryland','11':'District of Columbia',
    '51':'Virginia','54':'West Virginia','37':'North Carolina','45':'South Carolina',
    '13':'Georgia','12':'Florida'
}

out = in_corr[["STATEFP","COUNTYFP","GEOID","NAME"]].copy()
out["state"]  = out["STATEFP"].map(state_map)
out.rename(columns={"NAME":"county"}, inplace=True)
out = out.sort_values(["state","county"])

# --- Build BirdCast county URLs ---
state_fips_to_abbr = {
    "09":"CT","23":"ME","25":"MA","33":"NH","44":"RI","50":"VT",
    "34":"NJ","36":"NY","42":"PA","10":"DE","24":"MD","11":"DC",
    "51":"VA","54":"WV","37":"NC","45":"SC","13":"GA","12":"FL"
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
out[cols].to_csv("atlantic_flyway_corridor_counties_with_urls.csv", index=False)

# Save original format and GeoJSON too
out.to_csv("atlantic_flyway_corridor_counties.csv", index=False)
in_corr[["GEOID","geometry"]].to_file("atlantic_flyway_corridor_counties.geojson", driver="GeoJSON")
print("Files saved successfully!")

# Print a compact summary
print(f"Corridor width: ±{BUFFER_KM} km; Total counties: {len(out)}\n")
print(out.groupby("state")["county"].count().sort_values(ascending=False))
print("\nSample with BirdCast URLs:")
print(out[cols].head(10))
