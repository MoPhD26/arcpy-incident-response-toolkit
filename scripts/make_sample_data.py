"""Generate synthetic sample data for demos and tests.

All records are fictional. Coordinates are random points around Austin, TX,
with a few deliberately broken rows so the validator has something to catch.
"""

import csv
import random
from pathlib import Path

random.seed(42)
OUT = Path(__file__).resolve().parents[1] / "data"
CATEGORIES = ["FLOODING", "DOWNED POWER LINE", "ROAD CLOSURE", "WATER RESCUE"]


def incidents() -> None:
    rows = []
    for i in range(1, 26):
        lon = -97.74 + random.uniform(-0.04, 0.04)
        lat = 30.27 + random.uniform(-0.03, 0.03)
        rows.append([f"INC-{i:04d}", f"{lon:.6f}", f"{lat:.6f}", random.choice(CATEGORIES),
                     f"2026-06-{random.randint(1, 3):02d}T{random.randint(0, 23):02d}:00"])
    rows += [
        ["INC-0005", "-97.7301", "30.2702", "FLOODING", "2026-06-02T10:00"],      # duplicate id
        ["INC-0026", "30.2650", "-97.7420", "ROAD CLOSURE", "2026-06-02T11:00"],  # swapped lat/lon
        ["INC-0027", "", "30.2600", "FLOODING", "2026-06-02T12:00"],              # missing longitude
        ["INC-0028", "-80.1918", "25.7617", "WATER RESCUE", "2026-06-02T13:00"],  # outside Texas
        ["", "-97.7400", "30.2700", "FLOODING", "2026-06-02T14:00"],              # missing id
    ]
    with open(OUT / "sample_incidents.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["incident_id", "longitude", "latitude", "category", "reported"])
        w.writerows(rows)


if __name__ == "__main__":
    incidents()
    print(f"Wrote {OUT / 'sample_incidents.csv'}")
