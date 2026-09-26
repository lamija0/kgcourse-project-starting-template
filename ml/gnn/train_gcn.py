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

OUTPUT_DIR = (
    PROJECT_ROOT
    / "ml"
    / "gnn"
    / "output"
)

MODEL_FILE = OUTPUT_DIR / "gcn_model.pt"


# ============================================================
# Reproducibility
# ============================================================

torch.manual_seed(42)


# ============================================================
# Load graph
# ============================================================

data = torch.load(
    DATA_FILE,
    weights_only=False
)


# ============================================================
# GCN model
# ============================================================

class AccessibilityGCN(torch.nn.Module):
    def __init__(self, input_channels, hidden_channels, output_channels):
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

        x = F.dropout(
            x,
            p=0.3,
            training=self.training
        )

        x = self.conv2(
            x,
            edge_index
        )

        return x


model = AccessibilityGCN(
    input_channels=data.num_node_features,
    hidden_channels=32,
    output_channels=3
)


# ============================================================
# Optimizer
# ============================================================

optimizer = torch.optim.Adam(
    model.parameters(),
    lr=0.01,
    weight_decay=5e-4
)


# ============================================================
# Evaluation helper
# ============================================================

def accuracy(mask):
    model.eval()

    with torch.no_grad():
        output = model(
            data.x,
            data.edge_index
        )

        predictions = output.argmax(dim=1)

        correct = (
            predictions[mask]
            == data.y[mask]
        ).sum()

        total = int(mask.sum())

        return float(correct) / total


# ============================================================
# Training
# ============================================================

best_validation_accuracy = 0.0
best_model_state = None
best_epoch = 0

NUM_EPOCHS = 200

for epoch in range(1, NUM_EPOCHS + 1):
    model.train()

    optimizer.zero_grad()

    output = model(
        data.x,
        data.edge_index
    )

    loss = F.cross_entropy(
        output[data.train_mask],
        data.y[data.train_mask]
    )

    loss.backward()
    optimizer.step()

    validation_accuracy = accuracy(
        data.val_mask
    )

    if validation_accuracy > best_validation_accuracy:
        best_validation_accuracy = validation_accuracy
        best_epoch = epoch

        best_model_state = {
            key: value.detach().clone()
            for key, value
            in model.state_dict().items()
        }

    if epoch % 20 == 0:
        training_accuracy = accuracy(
            data.train_mask
        )

        print(
            f"Epoch {epoch:3d} | "
            f"Loss: {loss.item():.4f} | "
            f"Train Accuracy: "
            f"{training_accuracy:.3f} | "
            f"Validation Accuracy: "
            f"{validation_accuracy:.3f}"
        )


# ============================================================
# Restore best model
# ============================================================

if best_model_state is not None:
    model.load_state_dict(
        best_model_state
    )


# ============================================================
# Final evaluation
# ============================================================

train_accuracy = accuracy(
    data.train_mask
)

validation_accuracy = accuracy(
    data.val_mask
)

test_accuracy = accuracy(
    data.test_mask
)


# ============================================================
# Save model
# ============================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

torch.save(
    {
        "model_state_dict": model.state_dict(),
        "input_channels": data.num_node_features,
        "hidden_channels": 32,
        "output_channels": 3,
        "best_epoch": best_epoch,
        "train_accuracy": train_accuracy,
        "validation_accuracy": validation_accuracy,
        "test_accuracy": test_accuracy,
    },
    MODEL_FILE
)


# ============================================================
# Summary
# ============================================================

print()
print("GCN training finished.")
print("------------------------------------------")
print(f"Best epoch:          {best_epoch}")
print(f"Training accuracy:   {train_accuracy:.3f}")
print(f"Validation accuracy: {validation_accuracy:.3f}")
print(f"Test accuracy:       {test_accuracy:.3f}")
print("------------------------------------------")
print(f"Model saved to: {MODEL_FILE}")