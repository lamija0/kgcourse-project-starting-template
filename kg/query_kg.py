from pathlib import Path

from rdflib import Graph


PROJECT_ROOT = Path(__file__).resolve().parent.parent
KG_FILE = PROJECT_ROOT / "kg" / "output" / "vienna_kg.ttl"


graph = Graph()
graph.parse(KG_FILE, format="turtle")


query = """
PREFIX kg: <http://example.org/vienna-kg/>

SELECT ?flat ?price ?stop ?stopName
WHERE {
    ?flat a kg:Flat ;
          kg:nearStop ?stop .

    OPTIONAL {
        ?flat kg:price ?price .
    }

    OPTIONAL {
        ?stop kg:name ?stopName .
    }
}
LIMIT 10
"""


results = graph.query(query)

print(f"Loaded Knowledge Graph with {len(graph)} triples.")
print()
print("Example Flat -> nearStop -> Stop relations:")
print("--------------------------------------------")

for row in results:
    print(
        f"Flat: {row.flat}\n"
        f"Price: {row.price}\n"
        f"Stop: {row.stopName}\n"
        f"Stop URI: {row.stop}\n"
    )