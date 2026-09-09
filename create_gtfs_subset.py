import csv
import os

SRC = "src/assets/data/wienerlinien_full"
DST = "src/assets/data/wienerlinien"

os.makedirs(DST, exist_ok=True)

# --------------------------------------------------
# 1. Pro shape_id genau einen repräsentativen Trip
# --------------------------------------------------

selected_trips = {}
selected_shape_ids = set()

with open(
    os.path.join(SRC, "trips.txt"),
    encoding="utf-8-sig",
    newline=""
) as infile:

    reader = csv.DictReader(infile)

    for row in reader:
        shape_id = row["shape_id"]
        trip_id = row["trip_id"]

        if shape_id and shape_id not in selected_trips:
            selected_trips[shape_id] = row
            selected_shape_ids.add(shape_id)

selected_trip_ids = {
    row["trip_id"]
    for row in selected_trips.values()
}

print("Selected trips:", len(selected_trip_ids))
print("Selected shapes:", len(selected_shape_ids))


# --------------------------------------------------
# 2. trips.txt schreiben
# --------------------------------------------------

with open(
    os.path.join(SRC, "trips.txt"),
    encoding="utf-8-sig",
    newline=""
) as infile, open(
    os.path.join(DST, "trips.txt"),
    "w",
    encoding="utf-8",
    newline=""
) as outfile:

    reader = csv.DictReader(infile)
    writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)

    writer.writeheader()

    for row in reader:
        if row["trip_id"] in selected_trip_ids:
            writer.writerow(row)


# --------------------------------------------------
# 3. stop_times.txt filtern
# --------------------------------------------------

used_stop_ids = set()

with open(
    os.path.join(SRC, "stop_times.txt"),
    encoding="utf-8-sig",
    newline=""
) as infile, open(
    os.path.join(DST, "stop_times.txt"),
    "w",
    encoding="utf-8",
    newline=""
) as outfile:

    reader = csv.DictReader(infile)
    writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)

    writer.writeheader()

    for row in reader:
        if row["trip_id"] in selected_trip_ids:
            writer.writerow(row)
            used_stop_ids.add(row["stop_id"])

print("Used stop IDs:", len(used_stop_ids))


# --------------------------------------------------
# 4. stops.txt auf tatsächlich benutzte Stops filtern
# --------------------------------------------------

with open(
    os.path.join(SRC, "stops.txt"),
    encoding="utf-8-sig",
    newline=""
) as infile, open(
    os.path.join(DST, "stops.txt"),
    "w",
    encoding="utf-8",
    newline=""
) as outfile:

    reader = csv.DictReader(infile)
    writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)

    writer.writeheader()

    for row in reader:
        if row["stop_id"] in used_stop_ids:
            writer.writerow(row)


# --------------------------------------------------
# 5. shapes.txt filtern
# --------------------------------------------------

with open(
    os.path.join(SRC, "shapes.txt"),
    encoding="utf-8-sig",
    newline=""
) as infile, open(
    os.path.join(DST, "shapes.txt"),
    "w",
    encoding="utf-8",
    newline=""
) as outfile:

    reader = csv.DictReader(infile)
    writer = csv.DictWriter(outfile, fieldnames=reader.fieldnames)

    writer.writeheader()

    for row in reader:
        if row["shape_id"] in selected_shape_ids:
            writer.writerow(row)


print("\nSubset successfully created.")
