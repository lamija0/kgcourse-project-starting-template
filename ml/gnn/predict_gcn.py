import json
from pathlib import Path

import torch
import torch.nn.functional as F
from torch_geometric.nn import GCNConv


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]

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


# ============================================================
# Model definition
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
# Load data
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

checkpoint = torch.load(
    MODEL_FILE,
    map_location="cpu",
    weights_only=False
)


# ============================================================
# Restore model
# ============================================================

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
# Prediction
# ============================================================

with torch.no_grad():
    output = model(
        data.x,
        data.edge_index
    )

    predictions = output.argmax(dim=1)


# ============================================================
# Metadata
# ============================================================

class_names = {
    0: "Low",
    1: "Medium",
    2: "High"
}

index_to_node = {
    index: uri
    for uri, index
    in metadata["node_to_index"].items()
}


# ============================================================
# Evaluate test flats
# ============================================================

test_indices = torch.where(
    data.test_mask
)[0].tolist()

correct_examples = []
incorrect_examples = []

for index in test_indices:
    flat_uri = index_to_node[index]

    actual_class = int(
        data.y[index]
    )

    predicted_class = int(
        predictions[index]
    )

    route_count = metadata[
        "flat_accessible_route_counts"
    ][flat_uri]

    example = {
        "flat": flat_uri,
        "routes": route_count,
        "actual": class_names[actual_class],
        "predicted": class_names[predicted_class]
    }

    if actual_class == predicted_class:
        correct_examples.append(example)
    else:
        incorrect_examples.append(example)


# ============================================================
# Output
# ============================================================

print()
print("GCN accessibility predictions")
print("------------------------------------------")
print(
    f"Correct test predictions:   "
    f"{len(correct_examples)}/{len(test_indices)}"
)
print(
    f"Incorrect test predictions: "
    f"{len(incorrect_examples)}/{len(test_indices)}"
)

print()
print("CORRECT EXAMPLES")
print("------------------------------------------")

for example in correct_examples[:5]:
    print(f"Flat:      {example['flat']}")
    print(f"Routes:    {example['routes']}")
    print(f"Actual:    {example['actual']}")
    print(f"Predicted: {example['predicted']}")
    print()

print("INCORRECT EXAMPLES")
print("------------------------------------------")

for example in incorrect_examples[:5]:
    print(f"Flat:      {example['flat']}")
    print(f"Routes:    {example['routes']}")
    print(f"Actual:    {example['actual']}")
    print(f"Predicted: {example['predicted']}")
    print()