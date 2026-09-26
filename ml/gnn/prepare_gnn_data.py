import json
from pathlib import Path

import torch
from rdflib import Graph, Namespace, RDF
from torch_geometric.data import Data


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

KG_FILE = PROJECT_ROOT / "kg" / "output" / "vienna_kg.ttl"

OUTPUT_DIR = PROJECT_ROOT / "ml" / "gnn" / "data"
OUTPUT_FILE = OUTPUT_DIR / "gnn_data.pt"
METADATA_FILE = OUTPUT_DIR / "metadata.json"


# ============================================================
# RDF setup
# ============================================================

KG = Namespace("http://example.org/vienna-kg/")

graph = Graph()
graph.parse(KG_FILE, format="turtle")


# ============================================================
# Collect Flat and Stop nodes
# ============================================================

flat_nodes = sorted(
    {
        str(subject)
        for subject in graph.subjects(RDF.type, KG.Flat)
    }
)

stop_nodes = sorted(
    {
        str(subject)
        for subject in graph.subjects(RDF.type, KG.Stop)
    }
)

all_nodes = flat_nodes + stop_nodes

node_to_index = {
    uri: index
    for index, uri in enumerate(all_nodes)
}


# ============================================================
# Helper functions
# ============================================================

def get_float(subject_uri, predicate):
    value = graph.value(
        subject=subject_uri,
        predicate=predicate
    )

    if value is None:
        return 0.0

    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def min_max_normalize(values):
    minimum = min(values)
    maximum = max(values)

    if maximum == minimum:
        return [0.0 for _ in values]

    return [
        (value - minimum) / (maximum - minimum)
        for value in values
    ]


# ============================================================
# Stop statistics
#
# For each Stop:
# - number of Trips serving it
# - number of distinct Routes reachable through those Trips
# ============================================================

stop_trip_counts = {}
stop_route_counts = {}
stop_routes = {}

for stop_uri_string in stop_nodes:
    stop_uri = graph.namespace_manager.compute_qname(
        stop_uri_string
    ) if False else None

    from rdflib import URIRef
    stop_ref = URIRef(stop_uri_string)

    trips = set(
        graph.objects(
            stop_ref,
            KG.servedBy
        )
    )

    routes = set()

    for trip in trips:
        routes.update(
            graph.objects(
                trip,
                KG.belongsToRoute
            )
        )

    stop_trip_counts[stop_uri_string] = len(trips)
    stop_route_counts[stop_uri_string] = len(routes)
    stop_routes[stop_uri_string] = {
        str(route)
        for route in routes
    }


# ============================================================
# Flat attributes
# ============================================================

from rdflib import URIRef

flat_prices = []
flat_sizes = []
flat_rooms = []

for flat_uri_string in flat_nodes:
    flat_ref = URIRef(flat_uri_string)

    flat_prices.append(
        get_float(flat_ref, KG.price)
    )

    flat_sizes.append(
        get_float(flat_ref, KG.size)
    )

    flat_rooms.append(
        get_float(flat_ref, KG.numberOfRooms)
    )


normalized_prices = min_max_normalize(flat_prices)
normalized_sizes = min_max_normalize(flat_sizes)
normalized_rooms = min_max_normalize(flat_rooms)


# ============================================================
# Normalize Stop features
# ============================================================

stop_trip_values = [
    stop_trip_counts[stop]
    for stop in stop_nodes
]

stop_route_values = [
    stop_route_counts[stop]
    for stop in stop_nodes
]

normalized_trip_counts = min_max_normalize(
    stop_trip_values
)

normalized_route_counts = min_max_normalize(
    stop_route_values
)


# ============================================================
# Node features
#
# Feature vector:
#
# [
#   is_flat,
#   is_stop,
#   price,
#   size,
#   rooms,
#   number_of_routes,
#   number_of_trips
# ]
# ============================================================

features = []


# Flat features
for index, flat_uri in enumerate(flat_nodes):
    features.append([
        1.0,
        0.0,
        normalized_prices[index],
        normalized_sizes[index],
        normalized_rooms[index],
        0.0,
        0.0,
    ])


# Stop features
for index, stop_uri in enumerate(stop_nodes):
    features.append([
        0.0,
        1.0,
        0.0,
        0.0,
        0.0,
        normalized_route_counts[index],
        normalized_trip_counts[index],
    ])


x = torch.tensor(
    features,
    dtype=torch.float
)


# ============================================================
# Flat <-> Stop edges
#
# RDF contains:
# Flat -> nearStop -> Stop
#
# For message passing we make the graph undirected.
# ============================================================

edges = []

for flat_uri_string in flat_nodes:
    flat_ref = URIRef(flat_uri_string)

    for stop_ref in graph.objects(
        flat_ref,
        KG.nearStop
    ):
        stop_uri_string = str(stop_ref)

        if stop_uri_string not in node_to_index:
            continue

        flat_index = node_to_index[flat_uri_string]
        stop_index = node_to_index[stop_uri_string]

        # Flat -> Stop
        edges.append([
            flat_index,
            stop_index
        ])

        # Stop -> Flat
        edges.append([
            stop_index,
            flat_index
        ])


edge_index = torch.tensor(
    edges,
    dtype=torch.long
).t().contiguous()


# ============================================================
# Accessibility labels for Flat nodes
#
# Accessibility is based on the number of distinct public
# transport Routes reachable from all nearby Stops.
#
# The flats are divided into three classes:
#
# 0 = Low accessibility
# 1 = Medium accessibility
# 2 = High accessibility
#
# Thresholds are derived from the 33% and 66% quantiles.
# ============================================================

flat_accessible_route_counts = []

for flat_uri_string in flat_nodes:
    flat_ref = URIRef(flat_uri_string)

    accessible_routes = set()

    for stop_ref in graph.objects(
        flat_ref,
        KG.nearStop
    ):
        stop_uri_string = str(stop_ref)

        accessible_routes.update(
            stop_routes.get(
                stop_uri_string,
                set()
            )
        )

    flat_accessible_route_counts.append(
        len(accessible_routes)
    )


route_count_tensor = torch.tensor(
    flat_accessible_route_counts,
    dtype=torch.float
)

low_threshold = float(
    torch.quantile(
        route_count_tensor,
        0.33
    )
)

high_threshold = float(
    torch.quantile(
        route_count_tensor,
        0.66
    )
)


# Stop nodes do not receive classification labels.
y = torch.full(
    (len(all_nodes),),
    -1,
    dtype=torch.long
)


for index, route_count in enumerate(
    flat_accessible_route_counts
):
    if route_count <= low_threshold:
        label = 0

    elif route_count <= high_threshold:
        label = 1

    else:
        label = 2

    y[index] = label


# ============================================================
# Train / validation / test split
#
# Only Flat nodes participate in classification.
# 70% training
# 15% validation
# 15% testing
# ============================================================

generator = torch.Generator()
generator.manual_seed(42)

flat_indices = torch.arange(
    len(flat_nodes)
)

permutation = flat_indices[
    torch.randperm(
        len(flat_indices),
        generator=generator
    )
]

train_end = int(
    0.70 * len(flat_indices)
)

validation_end = int(
    0.85 * len(flat_indices)
)


train_indices = permutation[:train_end]

validation_indices = permutation[
    train_end:validation_end
]

test_indices = permutation[
    validation_end:
]


train_mask = torch.zeros(
    len(all_nodes),
    dtype=torch.bool
)

validation_mask = torch.zeros(
    len(all_nodes),
    dtype=torch.bool
)

test_mask = torch.zeros(
    len(all_nodes),
    dtype=torch.bool
)


train_mask[train_indices] = True
validation_mask[validation_indices] = True
test_mask[test_indices] = True


# ============================================================
# Create PyTorch Geometric graph
# ============================================================

data = Data(
    x=x,
    edge_index=edge_index,
    y=y,
    train_mask=train_mask,
    val_mask=validation_mask,
    test_mask=test_mask
)


# ============================================================
# Save data
# ============================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

torch.save(
    data,
    OUTPUT_FILE
)


# ============================================================
# Save metadata
# ============================================================

metadata = {
    "number_of_flats": len(flat_nodes),
    "number_of_stops": len(stop_nodes),
    "number_of_nodes": len(all_nodes),
    "number_of_edges": edge_index.shape[1],
    "number_of_features": x.shape[1],

    "accessibility_classes": {
        "0": "Low",
        "1": "Medium",
        "2": "High"
    },

    "low_threshold": low_threshold,
    "high_threshold": high_threshold,

    "train_flats": int(train_mask.sum()),
    "validation_flats": int(validation_mask.sum()),
    "test_flats": int(test_mask.sum()),

    "flat_accessible_route_counts": {
        flat_nodes[index]:
            flat_accessible_route_counts[index]
        for index in range(len(flat_nodes))
    },

    "node_to_index": node_to_index
}


with open(
    METADATA_FILE,
    "w",
    encoding="utf-8"
) as file:
    json.dump(
        metadata,
        file,
        indent=2
    )


# ============================================================
# Summary
# ============================================================

print()
print("GNN data preparation finished.")
print("------------------------------------------")
print(f"Flats:              {len(flat_nodes)}")
print(f"Stops:              {len(stop_nodes)}")
print(f"Total nodes:        {len(all_nodes)}")
print(f"Edges:              {edge_index.shape[1]}")
print(f"Features per node:  {x.shape[1]}")
print()
print("Accessibility thresholds:")
print(f"Low / Medium:       {low_threshold:.1f} routes")
print(f"Medium / High:      {high_threshold:.1f} routes")
print()
print(f"Training flats:     {int(train_mask.sum())}")
print(f"Validation flats:   {int(validation_mask.sum())}")
print(f"Test flats:         {int(test_mask.sum())}")
print("------------------------------------------")
print(f"Graph data: {OUTPUT_FILE}")
print(f"Metadata:   {METADATA_FILE}")