# Geobelic — Vineyard AI Field Challenge (Sireț3)

> **Deeptech GigaHack 2026** · Challenge Provider: **Marcaj** · Tekwill, Chișinău  

---

## 1. Project Overview

Geobelic transforms the **Sireț3** unannotated UAV RGB orthomosaic (~145 ha in Moldova, 311 GeoTIFF tiles in `EPSG:32635` at 0.025 m/px) into:
1. **Marcaj Pre-Annotations:** Compliant **CVAT for images 1.1** XML (`annotations.xml`) containing individual vine canopies, physical row axes with continuity classification, and non-overlapping inter-row ground corridors.
2. **Inspection & Cleanup Route:** An obstacle-avoiding walking route (`route.geojson`) starting and finishing at the organizer-supplied origin, strictly walking on permitted passages and inter-row ground.
3. **Block & Row Metrics:** Detailed geospatial measurements (`measurements.csv`) in horizontal 2D metres ($m$), square metres ($m^2$), and hectares ($ha$).

---

## 2. Environment Setup & Installation

Ensure you have **Python 3.10+** (Python 3.11–3.14 supported).

```bash
# 1. Clone the repository
git clone https://github.com/your-team/geobelic.git
cd geobelic

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install pinned dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## 3. Model Weights & Architecture

* **Model:** **YOLO26-Seg** (`yolo26s-seg`) with native end-to-end `Segment26` prediction head.
* **Pretrained Base:** Ultralytics YOLO26 Small segmentation weights (`yolo26s-seg.pt`).
* **Fine-Tuned Weights:** Saved at [`weights/best.pt`](weights/best.pt) (23.3 MB, tracked directly in this repository for zero-dependency reproduction).

---

## 4. Model Training

The model is trained on aerial vineyard segmentation datasets augmented with high-resolution $1024 \times 1024$ crops from the official Sireț3 annotated tiles.

### Step 4.1: Prepare Sireț3 Training Crops (Optional / Reproduce)
Extract $1024 \times 1024$ training chips directly from the official Sireț3 example tiles:
```bash
PYTHONPATH=. .venv/bin/python scripts/prepare_siret3_chips.py
```

### Step 4.2: Train YOLO26 Model
Run the training script (automatically detects Apple Silicon `mps`, NVIDIA `cuda:0`, or `cpu`):
```bash
PYTHONPATH=. .venv/bin/python scripts/train_yolo.py \
  --model yolo26s-seg.pt \
  --data dataset/vineyard_data.yaml \
  --epochs 30 \
  --imgsz 1024 \
  --batch 8 \
  --name yolo26_vineyard_full
```

#### Training Arguments:
* `--model`: Base weights (default: `yolo26s-seg.pt`).
* `--data`: Path to dataset YAML (default: `dataset/vineyard_data.yaml`).
* `--epochs`: Training epochs (default: `50`, converged at `30`).
* `--imgsz`: Training resolution (default: `1024`).
* `--batch`: Batch size (default: `8`).
* `--device`: Hardware device (`mps` for Apple Silicon GPU, `0` for CUDA, `cpu`).

Best checkpoint is automatically copied to `weights/best.pt`.

---

## 5. End-to-End Challenge Execution

Run the complete pipeline from raw GeoTIFF tiles to all required deliverables (`annotations.xml`, `measurements.csv`, and `route.geojson`) in a single command:

```bash
PYTHONPATH=. .venv/bin/python scripts/run_challenge.py \
  --tiles-dir assets/01_tiles/siret3_challenge_tiles_part1of5 \
  --weights weights/best.pt \
  --output-xml annotations.xml \
  --output-csv measurements.csv \
  --output-route route.geojson \
  --package-zip
```

### What the Pipeline Computes:
1. **Canopy Polygons (`vineyard`):** Detects individual vine canopy boundaries with YOLO26-Seg.
2. **Global Block Clustering (`vineyard_id`):** Clusters plants within 5m across tiles using a 2.5m buffer and cuts along roads/passages to assign persistent `V01, V02...` IDs.
3. **Cross-Tile Row Stitching (`row_id`):** Group collinear row polylines across adjacent tile boundaries within 0.40m tolerance, assigning persistent `V01-R01, V01-R02...` IDs.
4. **Continuity Assessment (`row_structure`):** Measures in-row distances. Rows with gaps $\ge 5\text{ m}$ are classified as `disrupted` (producing inspection targets); otherwise `regular`.
5. **Inter-Row Corridors (`interrow_area`):** Computes ground polygons between adjacent rows and strictly subtracts canopy polygons to **guarantee 0% overlap**.
6. **Ground Cover (`interrow_cover`):** Computes Excess Green index ($2G - R - B$) on ground pixels to classify `bare_soil` (<25%), `mixed` (25–75%), or `vegetation` (>75%).
7. **Agronomic Measurements (`measurements.csv`):** Per-row lengths ($m$), canopy and inter-row areas ($m^2, ha$), counts, and ground cover.
8. **Walking Route (`route.geojson`):** Delaunay dual graph on `passages.geojson` combined with inter-row corridors, solving TSP with 2-Opt optimization to visit all gaps $\ge 5\text{ m}$ and waste, returning to `(629504.70, 5220250.75)` within 5 m.

---

## 6. Interactive Web Dashboard

To launch the interactive Leaflet dashboard to inspect blocks, rows, measurements, and the walking route:

```bash
PYTHONPATH=. .venv/bin/python web/serve.py
```

Then open your browser at **[http://localhost:8080](http://localhost:8080)**.

* **Live Map:** Renders the Sireț3 survey area, route start point, authorized passages, forbidden zones, and the calculated TSP walking route.
* **KPI Metrics Bar:** Instant display of Block Count, Row Count, Total Row Length ($km$), Canopy Area ($ha$), Inter-row Area ($ha$), and Target Coverage.
* **Data Explorer Table:** Live search and filter through all physical rows and their agronomic attributes from `measurements.csv`.

---

## 7. Hardware Benchmark & Measured Performance

* **Benchmark Hardware:** Apple M5 Pro (16-core GPU, unified memory, Apple Silicon MPS).
* **Per-Tile Inference Time:** **$5.3\text{ ms}$** per $1024 \times 1024$ tile.
* **Batch Processing (74 tiles):** **$14.78\text{ seconds}$** total wall-clock time ($0.20\text{ s/tile}$ including full YOLO26 inference, global block clustering, cross-tile row stitching, interrow derivation, CSV metrics calculation, and TSP route solving).
* **Full Orthomosaic (311 tiles):** **$\approx 60\text{ seconds}$** complete end-to-end execution.
* **External APIs / LLMs:** **None.** All inference and spatial algorithms run 100% locally and offline.

---

## 8. Competition Deliverables

| Deliverable | Location | Description |
| :--- | :--- | :--- |
| **Route** | `route.geojson` | Valid LineString in `EPSG:32635` with `length_m`. Returns to `(629504.70, 5220250.75)` within 5 m (exact distance: 0.0 m). |
| **Measurements** | `measurements.csv` | Lengths ($m$) and areas ($m^2, ha$) by `vineyard_id` / `row_id`. |
| **Marcaj Import** | `annotations.xml` / `upload_submission.zip` | Exact Marcaj CVAT for images 1.1 XML format + images. |
| **Trained Weights** | [`weights/best.pt`](weights/best.pt) | Fine-tuned YOLO26-Seg model weights (23.3 MB). |
| **Web Dashboard** | [`web/`](web/) | Interactive Leaflet dashboard at `http://localhost:8080`. |

---

## 9. Licences & Attribution

* **Sireț3 UAV Imagery:** **CC BY 4.0** — Credit: *3DATA COLLECT / OpenAerialMap*, contributors to the Open Imagery Network.
* **Passages & Restrictions Vector Data:** Contains OpenStreetMap data, © OpenStreetMap contributors, **ODbL**.
* **Code:** MIT License.

