# Data

## Included

`sample_incidents.csv` is synthetic. It holds 30 fictional incident reports around Austin, TX. Five rows contain deliberate errors (a duplicate ID, swapped coordinates, a missing longitude, a point in Florida, and a missing ID) so the validator has something to catch. Regenerate it with:

```bash
python scripts/make_sample_data.py
```

## Public data for the ArcPy tools

To run the mapping and QA/QC tools end to end, build a file geodatabase from public sources:

| Layer | Source |
|---|---|
| Address points | City of Austin Open Data Portal, or the Texas Department of Information Resources StratMap address points |
| Flood hazard zones | FEMA National Flood Hazard Layer (NFHL) |
| Census tracts and blocks | U.S. Census Bureau TIGER/Line shapefiles |
| Shelters and facilities | Create your own test layer with fields NAME, STATUS, SHELTER_TYPE, CAPACITY, OCCUPANCY, LAST_INSPECTED |

Large datasets and geodatabases are excluded from version control by `.gitignore`.
