from pathlib import Path

from rdflib import Graph, Namespace


# ============================================================
# Paths
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

LOGIC_KG_FILE = PROJECT_ROOT / "kg" / "output" / "vienna_kg_logic_evolved.ttl"
ML_KG_FILE = PROJECT_ROOT / "kg" / "output" / "vienna_kg_ml_evolved.ttl"

KG = Namespace("http://example.org/vienna-kg/")


# ============================================================
# Service parameters
#
# "Well connected" = at least as many accessible route variants
# as the threshold of the High accessibility class (Section 3.2).
# ============================================================

MAX_PRICE = 900
MIN_ROUTE_VARIANTS = 43

LOW_THRESHOLD = 26
HIGH_THRESHOLD = 42


# ============================================================
# Load both evolved graphs into one combined Knowledge Graph
# (source data + accessibleViaRoute + hasPredictedAccessibility)
# ============================================================

graph = Graph()
graph.parse(LOGIC_KG_FILE, format="turtle")
graph.parse(ML_KG_FILE, format="turtle")
graph.bind("kg", KG)

print(f"Combined Knowledge Graph: {len(graph)} triples")


# ============================================================
# Service query:
# Which flats below MAX_PRICE are well connected to public
# transport?
# ============================================================

service_query = f"""
PREFIX kg: <http://example.org/vienna-kg/>

SELECT ?flat ?price
       (SAMPLE(?title) AS ?flatTitle)
       (SAMPLE(?predicted) AS ?gcnClass)
       (COUNT(DISTINCT ?route) AS ?routeVariants)
WHERE {{
    ?flat a kg:Flat ;
          kg:price ?price ;
          kg:accessibleViaRoute ?route .

    FILTER(?price <= {MAX_PRICE})

    OPTIONAL {{ ?flat kg:title ?title . }}
    OPTIONAL {{ ?flat kg:hasPredictedAccessibility ?predicted . }}
}}
GROUP BY ?flat ?price
HAVING (COUNT(DISTINCT ?route) >= {MIN_ROUTE_VARIANTS})
"""

results = list(graph.query(service_query))
results.sort(key=lambda row: (-int(row.routeVariants), float(row.price)))


# ============================================================
# Helper: rule-based accessibility class from the route count
# ============================================================

def rule_based_class(route_count):
    if route_count <= LOW_THRESHOLD:
        return "Low"
    if route_count <= HIGH_THRESHOLD:
        return "Medium"
    return "High"


# ============================================================
# Output
# ============================================================

print()
print(
    f"Flats with price <= {MAX_PRICE} EUR and "
    f">= {MIN_ROUTE_VARIANTS} accessible route variants: {len(results)}"
)
print("-" * 78)
print(f"{'Flat':<10}{'Price':>8}{'Routes':>8}  {'Rule class':<12}{'GCN class':<22}")
print("-" * 78)

agreements = 0

for row in results:
    flat = str(row.flat).split("/")[-1]
    route_count = int(row.routeVariants)
    rule_class = rule_based_class(route_count)

    gcn_class = (
        str(row.gcnClass).split("/")[-1].replace("Accessibility", "")
        if row.gcnClass is not None
        else "-"
    )

    if gcn_class == rule_class:
        agreements += 1

    print(
        f"flat/{flat:<5}{float(row.price):>8.0f}{route_count:>8}  "
        f"{rule_class:<12}{gcn_class:<22}"
    )

print("-" * 78)

if results:
    print(
        f"GCN prediction agrees with the rule-based class for "
        f"{agreements}/{len(results)} returned flats."
    )