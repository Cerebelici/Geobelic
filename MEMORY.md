# MEMORY.md — Vineyard AI Field Challenge (GigaHack 2026)

## 1. Project Overview & Objective
- **Problem Statement:** Turn **Sireț3** (unannotated UAV RGB orthomosaic of ~145 ha in Moldova, 3.52 cm/px) into an annotated vineyard map and an optimized walking inspection/cleanup route.
- **Economic Context:** Vineyard maintenance in Moldova costs 52,000–80,000 MDL/ha (~1.04–1.60M MDL for 20 ha). Optimizing walking route by 30% saves significant field labor/time during area audits for government subsidies.
- **Submission Deadline:** Sunday, 27 September, 15:00 Chișinău time (repository + frozen Marcaj project).

---

## 2. Coordinate System & Georeferencing Standards (CRITICAL)
- **Mandatory CRS:** `EPSG:32635` (`WGS 84 / UTM zone 35N`, unit: metres).
- **All exports must strictly adhere to EPSG:32635:**
  - `route.geojson` coordinates must be in EPSG:32635.
  - Geometry measurements: Horizontal 2D surface (no terrain/elevation correction).
  - Row lengths: metres ($m$).
  - Areas: square metres ($m^2$) and hectares ($ha$).

---

## 3. Annotation Schema & Conventions
Pre-annotations must be exported to **CVAT for images 1.1** (`annotations.xml`) inside the Marcaj upload zip.

| Target Class | Geometry Type | Label Name | Attributes & Permitted Values | Definition / Special Rules |
| :--- | :--- | :--- | :--- | :--- |
| **Grapevine Canopy** | `Polygon` | `vineyard` | `vineyard_id` (string/int) | Top-down canopy excluding ground. Adjacent canopies segmented individually (to allow vine counts). |
| **Waste** | `BoundingBox` | `waste` | `vineyard_id` (string/int) | Visible waste in & around vineyard. Separate objects when distinguishable; single bbox if inseparable cluster. Bounding box area $\neq$ waste area. |
| **Vine-Row Axis** | `Polyline` | `row` | `vineyard_id`, `row_id`, `row_structure` ∈ {`regular`, `disrupted`, `unassessable`} | Centerline along physical row axis. Gaps do NOT split row into new `row_id`. Inter-row axes NOT annotated. |
| **Inter-Row Area** | `Polygon` | `interrow_area` | `vineyard_id`, `interrow_cover` ∈ {`bare_soil`, `vegetation`, `mixed`, `unassessable`} | Ground between adjacent canopy rows within a block. Excludes canopies, roads, headlands, exterior land. Must not overlap canopy polygons. |
| **Inspection Target** | `Point` / `Target` | Derived / `inspection` | `vineyard_id`, `row_id`, `type` | Gaps in rows, missing plants, combined with waste bounding boxes as navigation targets. |

> **Note on "unassessable":** Use when image quality/shadows prevent clear determination. It is a strictly evaluated reference class.

---

## 4. Input Assets & Data Sources
- **Tiles:** 311 GeoTIFF tiles cut from Sireț3 orthomosaic (EPSG:32635).
- **Starting Point:** GeoJSON Point in EPSG:32635.
- **Passages & Restrictions:** GeoJSON `(Multi)Polygon` in EPSG:32635 with property `type = passage | forbidden`.
- **Open Reference Datasets:**
  - *Riseholme:* 855 UAV RGB images, COCO segmentations (canopy, rows).
  - *UOPNOA:* ~34k aerial RGB images + masks (land-use level).
  - *DroneWaste:* Aerial annotated waste dataset.

---

## 5. System Architecture & Technical Pipeline

```
[311 GeoTIFF Tiles]
       │
       ▼
┌────────────────────────────────────────────────────────┐
│ 1. AI Inference & Feature Extraction                   │
│    - Canopy Segmentation (YOLOv8/SAM/Mask R-CNN)       │
│    - Waste Detection (YOLOv8 / RT-DETR)                │
│    - Row Polyline Extraction (Classical CV + PCA/Hough)│
│    - Block Clustering (DBSCAN / Spatial Union)         │
│    - Row & Inter-row Attribute Classifiers             │
└────────────────────────────────────────────────────────┘
       │
       ├──────────────────────────────────────────┐
       ▼                                          ▼
┌───────────────────────────┐         ┌───────────────────────────────┐
│ 2. Marcaj Upload ZIP      │         │ 3. Spatial Processing Engine  │
│    - annotations.xml      │         │    - Inter-row polygon derive │
│    - images/ (311 tiles)  │         │    - Gap & Inspection targets │
│    (Manual team polishing)│         │    - Area / Length metrics    │
└───────────────────────────┘         └───────────────────────────────┘
                                                  │
                                                  ▼
                                      ┌───────────────────────────────┐
                                      │ 4. Route Optimization (TSP)   │
                                      │    - Network graph on通路     │
                                      │    - Avoid canopies/forbidden │
                                      │    - Pass start (±5m tolerance)│
                                      └───────────────────────────────┘
                                                  │
                                                  ▼
                                      ┌───────────────────────────────┐
                                      │ 5. Outputs & Web Dashboard    │
                                      │    - route.geojson            │
                                      │    - measurements.csv         │
                                      │    - Interactive Web Map (UI) │
                                      └───────────────────────────────┘
```

### A. Marcaj Platform Rules (Strict)
1. **Packaging:** `team_upload.zip` containing `annotations.xml` (CVAT for images 1.1) and `images/` (exact 311 `.tif` files, original filenames, unchanged).
2. **One-Shot Import:** Pre-annotations must be imported **BEFORE** publishing the project. Once published, only manual edits are allowed.
3. **Check Count:** Confirm exactly **311 files** in the project before publishing.
4. **Tile Stitching:** Ensure `vineyard_id` and `row_id` remain consistent across tile boundaries.

### B. Route Optimization Constraints
- **Start / End:** Must start and end at organizer-supplied starting point within **5 m tolerance**.
- **Path Validity:** Traverses **only** passable inter-row areas and authorized passages. **Never** through vine canopies, fences, or forbidden zones.
- **Targets:** Must visit all reachable waste locations and inspection points (row gaps / missing planting).
- **Objective:** Minimize total walking distance/time while achieving 100% reachable target coverage.
- **Export format:** `route.geojson` with geometry `LineString` and property `length_m`.

### C. Measurements Specification (`measurements.csv`)
Columns must detail:
- Block identifier (`vineyard_id`)
- Row identifier (`row_id`)
- Row length in metres ($m$)
- Canopy area in $m^2$ and $ha$ (dissolved/union of canopy polygons)
- Inter-row area in $m^2$ and $ha$
- Counts of unique blocks and rows

---

## 6. Deliverables Checklist for Submission

- [ ] **`route.geojson`**: Valid GeoJSON `LineString`, EPSG:32635, starts and returns to start point (within 5m), includes `length_m`.
- [ ] **`measurements.csv`**: Structured metrics per block/row (areas in $m^2$ and $ha$, lengths in $m$).
- [ ] **`README.md`**:
  - Exact reproduction instructions from raw tiles to final outputs.
  - Pinned dependencies (or Dockerfile).
  - Link/instructions to fetch model weights.
  - Processing runtime for the 311 tiles and benchmark hardware spec.
  - List of any external paid APIs / LLMs used.
  - Live link to the web interface demo.
- [ ] **Codebase**: AI models, spatial post-processing, routing engine, and web interface.
- [ ] **Marcaj Project**: All 311 jobs reviewed, corrected, and formally submitted before 15:00 Sunday.
- [ ] **Pitch Deck / Demo Plan**: 5-minute presentation + 5-minute Q&A demonstrating interactive map, metrics, ID consistency, and routing.