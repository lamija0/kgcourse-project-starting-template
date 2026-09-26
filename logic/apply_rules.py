from pathlib import Path

from rdflib import Graph, Namespace


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

KG_FILE = (
    PROJECT_ROOT
    / "kg"
    / "output"
    / "vienna_kg.ttl"
)

OUTPUT_FILE = (
    PROJECT_ROOT
    / "kg"
    / "output"
    / "vienna_kg_logic_evolved.ttl"
)


# ============================================================
# RDF setup
# ============================================================

KG = Namespace("http://example.org/vienna-kg/")

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
# Logical rule
#
# nearStop(F, S)
# AND servedBy(S, T)
# AND belongsToRoute(T, R)
#
# =>
#
# accessibleViaRoute(F, R)
# ============================================================

rule = """
PREFIX kg: <http://example.org/vienna-kg/>

CONSTRUCT {
    ?flat kg:accessibleViaRoute ?route .
}
WHERE {
    ?flat a kg:Flat ;
          kg:nearStop ?stop .

    ?stop kg:servedBy ?trip .

    ?trip kg:belongsToRoute ?route .
}
"""


# ============================================================
# Apply rule
# ============================================================

inferred_graph = graph.query(
    rule
).graph

new_triples = 0

for triple in inferred_graph:
    if triple not in graph:
        graph.add(triple)
        new_triples += 1


# ============================================================
# Save evolved graph
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
# Example query
#
# Which routes are accessible from Flat 0?
# ============================================================

example_query = """
PREFIX kg: <http://example.org/vienna-kg/>

SELECT ?route
WHERE {
    <http://example.org/vienna-kg/flat/0>
        kg:accessibleViaRoute
        ?route .
}
ORDER BY ?route
LIMIT 10
"""

results = list(
    graph.query(
        example_query
    )
)


# ============================================================
# Output
# ============================================================

print()
print("Logical reasoning finished.")
print("------------------------------------------------")
print(f"Original RDF triples: {original_triple_count}")
print(f"Inferred triples:     {new_triples}")
print(f"Evolved RDF triples:  {len(graph)}")
print()

print("Example inferred routes for flat/0:")
print("------------------------------------------------")

for row in results:
    print(row.route)

print("------------------------------------------------")
print(f"Output: {OUTPUT_FILE}")