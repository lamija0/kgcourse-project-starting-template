from pathlib import Path

from rdflib import Graph, Namespace


PROJECT_ROOT = Path(__file__).resolve().parents[2]

KG_FILE = PROJECT_ROOT / "kg" / "output" / "vienna_kg.ttl"

OUTPUT_DIR = PROJECT_ROOT / "ml" / "kge" / "data"
OUTPUT_FILE = OUTPUT_DIR / "triples.tsv"

KG = Namespace("http://example.org/vienna-kg/")


ALLOWED_RELATIONS = {
    KG.nearStop,
    KG.servedBy,
    KG.belongsToRoute,
    KG.followsShape,
}


graph = Graph()
graph.parse(KG_FILE, format="turtle")

triples = []

for subject, predicate, obj in graph:
    if predicate not in ALLOWED_RELATIONS:
        continue

    triples.append((
        str(subject),
        str(predicate),
        str(obj)
    ))


triples.sort()

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
    for subject, predicate, obj in triples:
        file.write(
            f"{subject}\t{predicate}\t{obj}\n"
        )


print("KGE triple export finished.")
print("---------------------------")
print(f"Source KG triples: {len(graph)}")
print(f"KGE triples:       {len(triples)}")
print(f"Output: {OUTPUT_FILE}")