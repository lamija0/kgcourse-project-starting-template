from pathlib import Path

from pykeen.pipeline import pipeline
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

OUTPUT_DIR = (
    PROJECT_ROOT
    / "ml"
    / "kge"
    / "output"
    / "transe"
)


# ============================================================
# Load triples
# ============================================================

triples_factory = TriplesFactory.from_path(
    TRIPLES_FILE
)

print("Loaded triples:")
print(f"Triples:   {triples_factory.num_triples}")
print(f"Entities:  {triples_factory.num_entities}")
print(f"Relations: {triples_factory.num_relations}")
print()


# ============================================================
# Train / validation / test split
# ============================================================

training, validation, testing = triples_factory.split(
    ratios=[0.8, 0.1, 0.1],
    random_state=42
)

print("Dataset split:")
print(f"Training:   {training.num_triples}")
print(f"Validation: {validation.num_triples}")
print(f"Testing:    {testing.num_triples}")
print()


# ============================================================
# Train TransE
# ============================================================

result = pipeline(
    training=training,
    validation=validation,
    testing=testing,

    model="TransE",

    model_kwargs={
        "embedding_dim": 64,
        "scoring_fct_norm": 1,
    },

    optimizer="Adam",

    optimizer_kwargs={
        "lr": 0.001,
    },

    training_kwargs={
        "num_epochs": 30,
        "batch_size": 1024,
    },

    random_seed=42,
    device="cpu",
)


# ============================================================
# Save model and results
# ============================================================

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True
)

result.save_to_directory(
    OUTPUT_DIR
)


# ============================================================
# Evaluation summary
# ============================================================

metrics = result.metric_results

print()
print("TransE training finished.")
print("-------------------------------------")
print(
    "MRR:",
    metrics.get_metric("both.realistic.inverse_harmonic_mean_rank")
)
print(
    "Hits@1:",
    metrics.get_metric("both.realistic.hits_at_1")
)
print(
    "Hits@10:",
    metrics.get_metric("both.realistic.hits_at_10")
)
print("-------------------------------------")
print(f"Model saved to: {OUTPUT_DIR}")