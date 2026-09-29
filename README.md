# Knowledge Graph Design for Exploring Public Transport Accessibility and Housing Prices in Vienna

This repository contains the code and data used for the Knowledge Graph portfolio project.

## Requirements

The project was tested with:

- Python 3.10
- Node.js 18
- npm
- Angular 15

Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Install the Angular dependencies:

```bash
npm install
```

## Data

The project uses two datasets.

### Vienna Public Transport Data

Vienna public transport data is provided in GTFS format.

The exact GTFS subset used for the experiments is included in:

```text
src/assets/data/wienerlinien/
```

The subset contains the relevant GTFS files:

```text
stops.txt
stop_times.txt
trips.txt
shapes.txt
```

The subset was created using:

```bash
python create_gtfs_subset.py
```

### Housing Data

The second dataset is a small, manually collected set of housing advertisements.

The raw JSON files are included in:

```text
helpers/wh/
```

The processed housing dataset is included in:

```text
src/assets/data/flat_info.json
```

The housing data was extracted using:

```text
helpers/extractor.py
```

## Knowledge Graph Construction

Construct the RDF Knowledge Graph with:

```bash
python kg/build_kg.py
```

This creates:

```text
kg/output/vienna_kg.ttl
```

The generated Knowledge Graph contains entities such as:

- Flat
- Stop
- Trip
- Route
- Shape

and relations such as:

- `nearStop`
- `servedBy`
- `belongsToRoute`
- `followsShape`

An example SPARQL query can be executed with:

```bash
python kg/query_kg.py
```

## Knowledge Graph Embeddings

Export the structural RDF triples used for the embedding experiment:

```bash
python ml/kge/export_triples.py
```

Train the TransE model with PyKEEN:

```bash
python ml/kge/train_transe.py
```

Evaluate example link predictions:

```bash
python ml/kge/predict_links.py
```

## Graph Neural Network

Prepare the PyTorch Geometric graph:

```bash
python ml/gnn/prepare_gnn_data.py
```

Train the Graph Convolutional Network:

```bash
python ml/gnn/train_gcn.py
```

Inspect example GCN predictions:

```bash
python ml/gnn/predict_gcn.py
```

Add the predicted accessibility classes back to the Knowledge Graph:

```bash
python ml/evolution/add_gcn_predictions_to_kg.py
```

This creates:

```text
kg/output/vienna_kg_ml_evolved.ttl
```

## Logical Reasoning

Apply the SPARQL `CONSTRUCT` rule that derives accessible public transport routes for flats:

```bash
python logic/apply_rules.py
```

This creates:

```text
kg/output/vienna_kg_logic_evolved.ttl
```

Run the recursive U-Bahn reachability example:

```bash
python logic/recursive_reachability.py
```

## Map Application

Start the Angular/Leaflet application with:

```bash
npm start
```

Then open:

```text
http://localhost:4200/
```

The map application visualizes the housing advertisements and GTFS data.

The RDF Knowledge Graph, logical reasoning, Knowledge Graph Embeddings, and GCN experiments are executed separately using the Python scripts described above.

## Recommended Execution Order

To reproduce the main project pipeline, run:

```bash
python kg/build_kg.py

python ml/kge/export_triples.py
python ml/kge/train_transe.py
python ml/kge/predict_links.py

python ml/gnn/prepare_gnn_data.py
python ml/gnn/train_gcn.py
python ml/gnn/predict_gcn.py
python ml/evolution/add_gcn_predictions_to_kg.py

python logic/apply_rules.py
python logic/recursive_reachability.py
```

## Generated Outputs

Generated RDF graphs, intermediate ML data, and trained model outputs are stored in the corresponding `output` and `data` directories.

The most important generated RDF files are:

```text
kg/output/vienna_kg.ttl
kg/output/vienna_kg_ml_evolved.ttl
kg/output/vienna_kg_logic_evolved.ttl
```

These outputs correspond to the results discussed in the portfolio report.

## Project Structure

```text
.
├── helpers/
│   ├── extractor.py
│   └── wh/
│
├── kg/
│   ├── build_kg.py
│   ├── query_kg.py
│   └── output/
│
├── logic/
│   ├── apply_rules.py
│   └── recursive_reachability.py
│
├── ml/
│   ├── evolution/
│   ├── gnn/
│   └── kge/
│
├── src/
│   └── assets/
│       └── data/
│           ├── flat_info.json
│           └── wienerlinien/
│
├── create_gtfs_subset.py
├── requirements.txt
└── README.md
```

## Notes

The included GTFS data is a reduced but consistent subset of the original Vienna public transport dataset. The subset is used by both the map application and the Knowledge Graph pipeline so that the experiments are based on the same underlying data.

The `route_id` values in the used Wiener Linien GTFS data represent route variants rather than unique public transport lines. Therefore, route counts reported by the project refer to route variants.