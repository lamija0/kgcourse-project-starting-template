import csv
import json
import math
from pathlib import Path
from urllib.parse import quote

from rdflib import Graph, Namespace, Literal, RDF, XSD


# ============================================================
# Configuration
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = PROJECT_ROOT / "src" / "assets" / "data"
GTFS_DIR = DATA_DIR / "wienerlinien"

FLATS_FILE = DATA_DIR / "flat_info.json"
STOPS_FILE = GTFS_DIR / "stops.txt"
TRIPS_FILE = GTFS_DIR / "trips.txt"
STOP_TIMES_FILE = GTFS_DIR / "stop_times.txt"
SHAPES_FILE = GTFS_DIR / "shapes.txt"

OUTPUT_DIR = PROJECT_ROOT / "kg" / "output"
OUTPUT_FILE = OUTPUT_DIR / "vienna_kg.ttl"

# Stops up to 500 metres from a flat are considered nearby.
NEAR_STOP_MAX_DISTANCE_M = 500


# ============================================================
# RDF graph
# ============================================================

graph = Graph()

KG = Namespace("http://example.org/vienna-kg/")
graph.bind("kg", KG)


# ============================================================
# Helper functions
# ============================================================

def safe_float(value):
    if value is None or value == "":
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def uri_part(value):
    return quote(str(value), safe="")


def normalize_stop_id(stop_id):
    """
    Convert GTFS platform-level stop IDs such as

        at:49:1018:0:1
        at:49:1018:0:2

    into one physical/meta stop:

        at:49:1018
    """
    parts = stop_id.split(":")

    if len(parts) >= 3:
        return ":".join(parts[:3])

    return stop_id


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Geographic distance between two coordinates in metres.
    """
    earth_radius_m = 6_371_000

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)

    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad)
        * math.cos(lat2_rad)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return earth_radius_m * c


# ============================================================
# 1. Housing data -> Flat entities
# ============================================================

with open(FLATS_FILE, "r", encoding="utf-8") as file:
    flats = json.load(file)

flat_locations = []

for index, flat in enumerate(flats):
    flat_uri = KG[f"flat/{index}"]

    graph.add((flat_uri, RDF.type, KG.Flat))

    price = safe_float(flat.get("PRICE"))
    latitude = safe_float(flat.get("LATITUDE"))
    longitude = safe_float(flat.get("LONGITUDE"))
    size = safe_float(flat.get("ESTATE_SIZE"))
    rooms = safe_float(flat.get("NUMBER_OF_ROOMS"))

    if price is not None:
        graph.add((
            flat_uri,
            KG.price,
            Literal(price, datatype=XSD.decimal)
        ))

    if flat.get("POSTCODE"):
        graph.add((
            flat_uri,
            KG.postcode,
            Literal(flat["POSTCODE"])
        ))

    if size is not None:
        graph.add((
            flat_uri,
            KG.size,
            Literal(size, datatype=XSD.decimal)
        ))

    if rooms is not None:
        graph.add((
            flat_uri,
            KG.numberOfRooms,
            Literal(rooms, datatype=XSD.decimal)
        ))

    if latitude is not None:
        graph.add((
            flat_uri,
            KG.latitude,
            Literal(latitude, datatype=XSD.decimal)
        ))

    if longitude is not None:
        graph.add((
            flat_uri,
            KG.longitude,
            Literal(longitude, datatype=XSD.decimal)
        ))

    if flat.get("PROPERTY_TYPE"):
        graph.add((
            flat_uri,
            KG.propertyType,
            Literal(flat["PROPERTY_TYPE"])
        ))

    if flat.get("HEADING"):
        graph.add((
            flat_uri,
            KG.title,
            Literal(flat["HEADING"])
        ))

    if latitude is not None and longitude is not None:
        flat_locations.append(
            (flat_uri, latitude, longitude)
        )


# ============================================================
# 2. GTFS stops -> physical/meta Stop entities
# ============================================================

meta_stops = {}
raw_stop_count = 0

with open(STOPS_FILE, "r", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)

    for stop in reader:
        raw_stop_id = stop.get("stop_id")

        if not raw_stop_id:
            continue

        raw_stop_count += 1

        meta_stop_id = normalize_stop_id(raw_stop_id)

        if meta_stop_id not in meta_stops:
            meta_stops[meta_stop_id] = {
                "preferred_name": None,
                "fallback_name": None,
                "preferred_coordinates": None,
                "coordinates": [],
                "platform_ids": set()
            }

        entry = meta_stops[meta_stop_id]

        entry["platform_ids"].add(raw_stop_id)

        stop_name = stop.get("stop_name")

        if stop_name:
            if entry["fallback_name"] is None:
                entry["fallback_name"] = stop_name

            # Prefer information from the actual meta-stop row,
            # if such a row exists.
            if raw_stop_id == meta_stop_id:
                entry["preferred_name"] = stop_name

        latitude = safe_float(stop.get("stop_lat"))
        longitude = safe_float(stop.get("stop_lon"))

        if latitude is not None and longitude is not None:
            entry["coordinates"].append(
                (latitude, longitude)
            )

            if raw_stop_id == meta_stop_id:
                entry["preferred_coordinates"] = (
                    latitude,
                    longitude
                )


stop_locations = []
meta_stop_ids = set(meta_stops.keys())

for meta_stop_id, data in meta_stops.items():
    stop_uri = KG[f"stop/{uri_part(meta_stop_id)}"]

    graph.add((stop_uri, RDF.type, KG.Stop))

    graph.add((
        stop_uri,
        KG.stopId,
        Literal(meta_stop_id)
    ))

    name = (
        data["preferred_name"]
        or data["fallback_name"]
    )

    if name:
        graph.add((
            stop_uri,
            KG.name,
            Literal(name)
        ))

    # Prefer coordinates belonging directly to the meta-stop.
    # Otherwise use the average location of its platforms.
    if data["preferred_coordinates"]:
        latitude, longitude = data["preferred_coordinates"]

    elif data["coordinates"]:
        latitude = sum(
            coordinate[0]
            for coordinate in data["coordinates"]
        ) / len(data["coordinates"])

        longitude = sum(
            coordinate[1]
            for coordinate in data["coordinates"]
        ) / len(data["coordinates"])

    else:
        latitude = None
        longitude = None

    if latitude is not None and longitude is not None:
        graph.add((
            stop_uri,
            KG.latitude,
            Literal(latitude, datatype=XSD.decimal)
        ))

        graph.add((
            stop_uri,
            KG.longitude,
            Literal(longitude, datatype=XSD.decimal)
        ))

        stop_locations.append(
            (
                stop_uri,
                latitude,
                longitude
            )
        )


# ============================================================
# 3. GTFS trips -> Trip and Route entities
# ============================================================

trip_count = 0
trip_ids = set()
route_ids = set()

trip_shape_links = []

with open(TRIPS_FILE, "r", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)

    for trip in reader:
        trip_id = trip.get("trip_id")

        if not trip_id:
            continue

        trip_uri = KG[f"trip/{uri_part(trip_id)}"]

        trip_ids.add(trip_id)

        graph.add((trip_uri, RDF.type, KG.Trip))

        graph.add((
            trip_uri,
            KG.tripId,
            Literal(trip_id)
        ))

        # ----------------------------------------------------
        # Route
        # ----------------------------------------------------

        route_id = trip.get("route_id")

        if route_id:
            route_uri = KG[f"route/{uri_part(route_id)}"]

            if route_id not in route_ids:
                graph.add((
                    route_uri,
                    RDF.type,
                    KG.Route
                ))

                graph.add((
                    route_uri,
                    KG.routeId,
                    Literal(route_id)
                ))

                route_ids.add(route_id)

            graph.add((
                trip_uri,
                KG.belongsToRoute,
                route_uri
            ))

        # ----------------------------------------------------
        # Trip attributes
        # ----------------------------------------------------

        if trip.get("trip_headsign"):
            graph.add((
                trip_uri,
                KG.headsign,
                Literal(trip["trip_headsign"])
            ))

        if trip.get("direction_id"):
            graph.add((
                trip_uri,
                KG.directionId,
                Literal(trip["direction_id"])
            ))

        shape_id = trip.get("shape_id")

        if shape_id:
            trip_shape_links.append(
                (trip_uri, shape_id)
            )

        trip_count += 1


# ============================================================
# 4. GTFS shapes -> Shape entities
# ============================================================

shape_ids = set()

with open(SHAPES_FILE, "r", encoding="utf-8-sig") as file:
    reader = csv.DictReader(file)

    for row in reader:
        shape_id = row.get("shape_id")

        if not shape_id:
            continue

        if shape_id in shape_ids:
            continue

        shape_uri = KG[f"shape/{uri_part(shape_id)}"]

        graph.add((
            shape_uri,
            RDF.type,
            KG.Shape
        ))

        graph.add((
            shape_uri,
            KG.shapeId,
            Literal(shape_id)
        ))

        shape_ids.add(shape_id)


# ============================================================
# 5. Trip -> Shape relations
# ============================================================

trip_shape_relations = set()

for trip_uri, shape_id in trip_shape_links:
    if shape_id not in shape_ids:
        continue

    shape_uri = KG[f"shape/{uri_part(shape_id)}"]

    relation = (
        trip_uri,
        KG.followsShape,
        shape_uri
    )

    graph.add(relation)
    trip_shape_relations.add(relation)


# ============================================================
# 6. Stop -> Trip relations
#
# Platform-level IDs from stop_times.txt are normalized to
# physical/meta stops.
# ============================================================

served_by_relations = set()

with open(
    STOP_TIMES_FILE,
    "r",
    encoding="utf-8-sig"
) as file:

    reader = csv.DictReader(file)

    for stop_time in reader:
        raw_stop_id = stop_time.get("stop_id")
        trip_id = stop_time.get("trip_id")

        if not raw_stop_id or not trip_id:
            continue

        meta_stop_id = normalize_stop_id(raw_stop_id)

        if meta_stop_id not in meta_stop_ids:
            continue

        if trip_id not in trip_ids:
            continue

        stop_uri = KG[
            f"stop/{uri_part(meta_stop_id)}"
        ]

        trip_uri = KG[
            f"trip/{uri_part(trip_id)}"
        ]

        relation = (
            stop_uri,
            KG.servedBy,
            trip_uri
        )

        if relation not in served_by_relations:
            graph.add(relation)
            served_by_relations.add(relation)


# ============================================================
# 7. Flat -> Stop integration
#
# Connect both originally independent datasets using their
# geographic coordinates.
# ============================================================

near_stop_relations = set()

for flat_uri, flat_lat, flat_lon in flat_locations:

    for stop_uri, stop_lat, stop_lon in stop_locations:

        distance = haversine_distance(
            flat_lat,
            flat_lon,
            stop_lat,
            stop_lon
        )

        if distance <= NEAR_STOP_MAX_DISTANCE_M:
            relation = (
                flat_uri,
                KG.nearStop,
                stop_uri
            )

            if relation not in near_stop_relations:
                graph.add(relation)
                near_stop_relations.add(relation)


# ============================================================
# 8. Save Knowledge Graph
# ============================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

graph.serialize(
    destination=str(OUTPUT_FILE),
    format="turtle"
)


# ============================================================
# Summary
# ============================================================

print()
print("Knowledge Graph construction finished.")
print("------------------------------------------")
print(f"Flats:                    {len(flats)}")
print(f"Raw GTFS stop records:    {raw_stop_count}")
print(f"Physical/meta stops:      {len(meta_stops)}")
print(f"Trips:                    {trip_count}")
print(f"Routes:                   {len(route_ids)}")
print(f"Shapes:                   {len(shape_ids)}")
print(
    f"Stop -> Trip relations:   "
    f"{len(served_by_relations)}"
)
print(
    f"Trip -> Shape relations:  "
    f"{len(trip_shape_relations)}"
)
print(
    f"Flat -> Stop relations:   "
    f"{len(near_stop_relations)}"
)
print("------------------------------------------")
print(f"Total RDF triples:        {len(graph)}")
print(f"Output: {OUTPUT_FILE}")