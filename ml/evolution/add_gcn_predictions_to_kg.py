import json
from pathlib import Path

import torch
import torch.nn.functional as F
from rdflib import Graph, Namespace, URIRef
from torch_geometric.nn import GCNConv


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

KG_FILE = (
    PROJECT_ROOT
    / "kg"
    / "output"
    / "vienna_kg.ttl"
)

DATA_FILE = (
    PROJECT_ROOT
    / "ml"
    / "gnn"
    / "data"
    / "gnn_data.pt"
)

METADATA_FILE = (
    PROJECT_ROOT
    / "ml"
    / "gnn"
    / "data"
    / "metadata.json"
)

MODEL_FILE = (
    PROJECT_ROOT
    / "ml"
    / "gnn"
    / "output"
    / "gcn_model.pt"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "kg"
    / "output"
    / "vienna_kg_ml_evolved.ttl"
)


# ============================================================
# Namespace
# ============================================================

KG = Namespace("http://example.org/vienna-kg/")


# ============================================================
# GCN model
# ============================================================

class AccessibilityGCN(torch.nn.Module):
    def __init__(
        self,
        input_channels,
        hidden_channels,
        output_channels
    ):
        super().__init__()

        self.conv1 = GCNConv(
            input_channels,
            hidden_channels
        )

        self.conv2 = GCNConv(
            hidden_channels,
            output_channels
        )

    def forward(self, x, edge_index):
        x = self.conv1(
            x,
            edge_index
        )

        x = F.relu(x)

        x = self.conv2(
            x,
            edge_index
        )

        return x


# ============================================================
# Load GNN data
# ============================================================

data = torch.load(
    DATA_FILE,
    weights_only=False
)

with open(
    METADATA_FILE,
    "r",
    encoding="utf-8"
) as file:
    metadata = json.load(file)


# ============================================================
# Load trained model
# ============================================================

checkpoint = torch.load(
    MODEL_FILE,
    map_location="cpu",
    weights_only=False
)

model = AccessibilityGCN(
    input_channels=checkpoint["input_channels"],
    hidden_channels=checkpoint["hidden_channels"],
    output_channels=checkpoint["output_channels"]
)

model.load_state_dict(
    checkpoint["model_state_dict"]
)

model.eval()


# ============================================================
# Predict accessibility classes
# ============================================================

with torch.no_grad():
    output = model(
        data.x,
        data.edge_index
    )

    predictions = output.argmax(
        dim=1
    )


# ============================================================
# Accessibility class URIs
# ============================================================

accessibility_classes = {
    0: KG.LowAccessibility,
    1: KG.MediumAccessibility,
    2: KG.HighAccessibility
}

accessibility_names = {
    0: "Low",
    1: "Medium",
    2: "High"
}


# ============================================================
# Load original RDF graph
# ============================================================

graph = Graph()
graph.parse(
    KG_FILE,
    format="turtle"
)

graph.bind(
    "kg",
    KG
)

original_triple_count = len(graph)


# ============================================================
# Add GCN predictions to Knowledge Graph
#
# Example:
#
# flat/113
#     kg:hasPredictedAccessibility
#     kg:HighAccessibility .
# ============================================================

added_predictions = []

node_to_index = metadata[
    "node_to_index"
]

for node_uri, node_index in node_to_index.items():

    # Only Flat nodes receive accessibility predictions.
    if "/flat/" not in node_uri:
        continue

    predicted_class = int(
        predictions[node_index]
    )

    flat_ref = URIRef(
        node_uri
    )

    accessibility_ref = accessibility_classes[
        predicted_class
    ]

    triple = (
        flat_ref,
        KG.hasPredictedAccessibility,
        accessibility_ref
    )

    if triple not in graph:
        graph.add(
            triple
        )

        added_predictions.append({
            "flat": node_uri,
            "prediction":
                accessibility_names[predicted_class]
        })


# ============================================================
# Save evolved Knowledge Graph
# ============================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

graph.serialize(
    destination=OUTPUT_FILE,
    format="turtle"
)


# ============================================================
# Summary
# ============================================================

print()
print("ML-based Knowledge Graph evolution finished.")
print("------------------------------------------------")
print(f"Original RDF triples: {original_triple_count}")
print(f"Predictions added:    {len(added_predictions)}")
print(f"Evolved RDF triples:  {len(graph)}")
print()

print("Example new triples:")
print("------------------------------------------------")

for prediction in added_predictions[:5]:
    print(
        f"{prediction['flat']} "
        f"--hasPredictedAccessibility--> "
        f"{prediction['prediction']}"
    )

print("------------------------------------------------")
print(f"Output: {OUTPUT_FILE}")