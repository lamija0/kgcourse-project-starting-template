import math
from pathlib import Path

import torch
from rdflib import Graph, Namespace, URIRef
from pykeen.triples import TriplesFactory


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TRIPLES_FILE = (
    PROJECT_ROOT
    / "ml"
    / "kge"
    / "data"
    / "triples.tsv"
)

MODEL_FILE = (
    PROJECT_ROOT
    / "ml"
    / "kge"
    / "output"
    / "transe"
    / "trained_model.pkl"
)

KG_FILE = (
    PROJECT_ROOT
    / "kg"
    / "output"
    / "vienna_kg.ttl"
)


# ============================================================
# Configuration
# ============================================================

KG = Namespace("http://example.org/vienna-kg/")

FLAT_URI = "http://example.org/vienna-kg/flat/0"
RELATION_URI = "http://example.org/vienna-kg/nearStop"

MAX_DISTANCE_M = 500


# ============================================================
# Helper
# ============================================================

def haversine_distance(lat1, lon1, lat2, lon2):
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

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return earth_radius_m * c


# ============================================================
# Load mappings
# ============================================================

triples_factory = TriplesFactory.from_path(TRIPLES_FILE)

head_id = triples_factory.entity_to_id[FLAT_URI]
relation_id = triples_factory.relation_to_id[RELATION_URI]

id_to_entity = {
    entity_id: entity
    for entity, entity_id
    in triples_factory.entity_to_id.items()
}


# ============================================================
# Load trained TransE model
# ============================================================

model = torch.load(
    MODEL_FILE,
    map_location="cpu",
    weights_only=False
)

model.eval()


# ============================================================
# Score all possible tails for
#
# Flat 0 --nearStop--> ?
# ============================================================

hr_batch = torch.tensor(
    [[head_id, relation_id]],
    dtype=torch.long
)

with torch.inference_mode():
    scores = model.score_t(hr_batch)[0]


ranked_entity_ids = torch.argsort(
    scores,
    descending=True
).tolist()


# ============================================================
# Load RDF graph for geographic validation
# ============================================================

graph = Graph()
graph.parse(KG_FILE, format="turtle")

flat_ref = URIRef(FLAT_URI)

flat_lat = float(graph.value(flat_ref, KG.latitude))
flat_lon = float(graph.value(flat_ref, KG.longitude))


# ============================================================
# Find one true positive and one false positive
# ============================================================

true_positive = None
false_positive = None

for entity_id in ranked_entity_ids:
    entity_uri = id_to_entity[entity_id]

    # Only Stop entities are meaningful targets for nearStop.
    if "/stop/" not in entity_uri:
        continue

    stop_ref = URIRef(entity_uri)

    lat_value = graph.value(stop_ref, KG.latitude)
    lon_value = graph.value(stop_ref, KG.longitude)

    if lat_value is None or lon_value is None:
        continue

    stop_lat = float(lat_value)
    stop_lon = float(lon_value)

    distance = haversine_distance(
        flat_lat,
        flat_lon,
        stop_lat,
        stop_lon
    )

    stop_name = graph.value(stop_ref, KG.name)

    prediction = {
        "stop": entity_uri,
        "name": str(stop_name) if stop_name else "Unknown",
        "distance": distance,
        "score": float(scores[entity_id]),
    }

    if distance <= MAX_DISTANCE_M and true_positive is None:
        true_positive = prediction

    if distance > MAX_DISTANCE_M and false_positive is None:
        false_positive = prediction

    if true_positive and false_positive:
        break


# ============================================================
# Output
# ============================================================

print("Prediction task:")
print(f"{FLAT_URI} --nearStop--> ?")
print()

print("TRUE POSITIVE")
print("-------------")
print(f"Stop:     {true_positive['name']}")
print(f"URI:      {true_positive['stop']}")
print(f"Distance: {true_positive['distance']:.1f} m")
print(f"Score:    {true_positive['score']:.4f}")
print()

print("FALSE POSITIVE")
print("--------------")
print(f"Stop:     {false_positive['name']}")
print(f"URI:      {false_positive['stop']}")
print(f"Distance: {false_positive['distance']:.1f} m")
print(f"Score:    {false_positive['score']:.4f}")