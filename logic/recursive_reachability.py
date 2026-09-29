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

KG = Namespace("http://example.org/vienna-kg/")

graph = Graph()
graph.parse(KG_FILE, format="turtle")
graph.bind("kg", KG)


# ============================================================
# Rule: direct U-Bahn connection between two stops
#
# connectedByUBahn(S1, S2) :-
#     servedBy(S1, T), servedBy(S2, T),
#     belongsToRoute(T, R), isUBahnRoute(R), S1 != S2.
#
# U-Bahn route variants are recognized by their route_id,
# e.g. 21-U4-j26-1.
# ============================================================

rule = """
PREFIX kg: <http://example.org/vienna-kg/>

CONSTRUCT {
    ?stop1 kg:connectedByUBahn ?stop2 .
}
WHERE {
    ?trip kg:belongsToRoute ?route .
    FILTER(REGEX(STR(?route), "-U[0-9]-"))

    ?stop1 kg:servedBy ?trip .
    ?stop2 kg:servedBy ?trip .
    FILTER(?stop1 != ?stop2)
}
"""

inferred = graph.query(rule).graph

new_triples = 0
for triple in inferred:
    if triple not in graph:
        graph.add(triple)
        new_triples += 1


# ============================================================
# Recursive query: all stops reachable from flat/0 using only
# the U-Bahn network, with arbitrarily many transfers.
#
# reachable(S1, S2) :- connectedByUBahn(S1, S2).
# reachable(S1, S3) :- reachable(S1, S2), connectedByUBahn(S2, S3).
#
# In SPARQL, the recursion is expressed by the property path "+".
# ============================================================

recursive_query = """
PREFIX kg: <http://example.org/vienna-kg/>

SELECT DISTINCT ?stop ?name
WHERE {
    <http://example.org/vienna-kg/flat/0> kg:nearStop ?start .
    ?start kg:connectedByUBahn+ ?stop .

    OPTIONAL { ?stop kg:name ?name . }
}
ORDER BY ?name
"""

results = list(graph.query(recursive_query))


# ============================================================
# Output
# ============================================================

print()
print("Recursive U-Bahn reachability")
print("------------------------------------------------")
print(f"Derived connectedByUBahn triples: {new_triples}")
print(f"Stops reachable from flat/0 via U-Bahn: {len(results)}")
print()
print("First 10 reachable stops:")
for row in results[:10]:
    print(f"  {row.name}")
print("------------------------------------------------")