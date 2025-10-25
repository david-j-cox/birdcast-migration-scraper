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

# Keep only states in/near the Mississippi corridor to speed things up
print("Filtering to Mississippi corridor states...")
keep_statefps = {
    "27","55","19","17","29",        # MN, WI, IA, IL, MO
    "38","46","31","20","40",        # ND, SD, NE, KS, OK
    "05","22","28","47","01",        # AR, LA, MS, TN, AL
    "21","18","39","26","48",        # KY, IN, OH, MI, TX
    "30","56","08","35"              # MT, WY, CO, NM
}
counties = counties[counties["STATEFP"].isin(keep_statefps)].copy()
print(f"Filtered to {len(counties)} counties in Mississippi corridor states")

# -----------------------------
# 2) Define the corridor spine
# -----------------------------
# Mississippi Flyway route from Canada to Gulf of Mexico
spine_ll = LineString([
    (-94.685, 46.729),   # Bemidji, Minnesota (northern lakes)
    (-94.636, 46.353),   # Park Rapids, Minnesota
    (-94.201, 45.566),   # St. Cloud, Minnesota
    (-93.094, 44.944),   # Minneapolis/St. Paul, Minnesota
    (-91.499, 43.804),   # La Crosse, Wisconsin
    (-91.124, 43.203),   # Dubuque, Iowa
    (-90.579, 41.524),   # Davenport, Iowa
    (-90.515, 40.552),   # Burlington, Iowa
    (-91.106, 39.739),   # Hannibal, Missouri
    (-90.199, 38.627),   # St. Louis, Missouri
    (-89.139, 36.970),   # Cape Girardeau, Missouri
    (-89.928, 35.927),   # New Madrid, Missouri
    (-90.048, 35.149),   # Memphis, Tennessee
    (-91.154, 33.216),   # Vicksburg, Mississippi
    (-91.187, 32.299),   # Natchez, Mississippi
    (-91.140, 30.458),   # Baton Rouge, Louisiana
    (-90.072, 29.951),   # New Orleans, Louisiana
])

# -------------------------------------------
# 3) Buffer by a fixed kilometer width
# -------------------------------------------
# Project to CONUS Albers (meters) for accurate buffering
print("Projecting coordinates and creating corridor buffer...")
ALBERS = 5070
counties_alb = counties.to_crs(ALBERS)
spine_alb   = gpd.GeoSeries([spine_ll], crs=4326).to_crs(ALBERS).iloc[0]

BUFFER_KM = 130  # << set corridor half-width (slightly wider for Mississippi River basin)
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
    '27':'Minnesota','55':'Wisconsin','19':'Iowa','17':'Illinois','29':'Missouri',
    '38':'North Dakota','46':'South Dakota','31':'Nebraska','20':'Kansas','40':'Oklahoma',
    '05':'Arkansas','22':'Louisiana','28':'Mississippi','47':'Tennessee','01':'Alabama',
    '21':'Kentucky','18':'Indiana','39':'Ohio','26':'Michigan','48':'Texas',
    '30':'Montana','56':'Wyoming','08':'Colorado','35':'New Mexico'
}

out = in_corr[["STATEFP","COUNTYFP","GEOID","NAME"]].copy()
out["state"]  = out["STATEFP"].map(state_map)
out.rename(columns={"NAME":"county"}, inplace=True)
out = out.sort_values(["state","county"])

# --- Build BirdCast county URLs ---
state_fips_to_abbr = {
    "27":"MN","55":"WI","19":"IA","17":"IL","29":"MO",
    "38":"ND","46":"SD","31":"NE","20":"KS","40":"OK",
    "05":"AR","22":"LA","28":"MS","47":"TN","01":"AL",
    "21":"KY","18":"IN","39":"OH","26":"MI","48":"TX",
    "30":"MT","56":"WY","08":"CO","35":"NM"
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
out[cols].to_csv("mississippi_flyway_corridor_counties_with_urls.csv", index=False)

# Save original format and GeoJSON too
out.to_csv("mississippi_flyway_corridor_counties.csv", index=False)
in_corr[["GEOID","geometry"]].to_file("mississippi_flyway_corridor_counties.geojson", driver="GeoJSON")
print("Files saved successfully!")

# Print a compact summary
print(f"Corridor width: ±{BUFFER_KM} km; Total counties: {len(out)}\n")
print(out.groupby("state")["county"].count().sort_values(ascending=False))
print("\nSample with BirdCast URLs:")
print(out[cols].head(10))
