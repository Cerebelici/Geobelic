# Geobelic

Vineyard AI Field Challenge (Sireț3), Deeptech GigaHack 2026. The knowledge base is [knowledge/README.md](knowledge/README.md).

The participant package is in `assets/`. Sireț3 imagery is **CC BY 4.0** — credit 3DATA COLLECT / OpenAerialMap, contributors to the Open Imagery Network. The licence allows reuse, adaptation, and redistribution, including commercial use, with that attribution. Route layers include OpenStreetMap data, © OpenStreetMap contributors, ODbL.

The source orthomosaic (`assets/04_source/siret3_source_orthomosaic_EPSG4326.tif`) is stored with Git LFS. After cloning, run `git lfs pull` if that file is only a pointer.
# Geobelic — Vineyard AI Field Challenge (Sireț3)

> **Deeptech GigaHack 2026** · Challenge Provider: **Marcaj** · Tekwill, Chișinău  
> Single Source of Truth Documentation: [`knowledge/README.md`](knowledge/README.md) · Operational Reference: [`MEMORY.md`](MEMORY.md)

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

## 5. Model Inference & Marcaj CVAT 1.1 Generation

The inference tool processes raw GeoTIFF tiles, performs geometric extraction, and generates the exact **CVAT for images 1.1 `annotations.xml`** without creating intermediate image files.

### Basic Command:
```bash
PYTHONPATH=. .venv/bin/python scripts/generate_cvat.py \
  --source assets/05_examples/siret3_examples_cvat/images \
  --weights weights/best.pt \
  --output annotations.xml \
  --conf 0.28
```

### Process All Challenge Tiles:
```bash
PYTHONPATH=. .venv/bin/python scripts/generate_cvat.py \
  --source path/to/311_challenge_tiles \
  --weights weights/best.pt \
  --output annotations.xml \
  --conf 0.28 \
  --imgsz 1024
```

### Export Raw Coordinates to JSON (Optional):
```bash
PYTHONPATH=. .venv/bin/python scripts/generate_cvat.py \
  --source assets/05_examples/siret3_examples_cvat/images \
  --weights weights/best.pt \
  --output annotations.xml \
  --save-json coordinates.json
```

### What the Pipeline Computes:
1. **Canopy Polygons (`vineyard`):** Detects individual vine canopy boundaries.
2. **Row Centerlines (`row`):** Estimates dominant block azimuth using a nearest-neighbor directional histogram and fits smooth centerlines within 0.2 m of vine centers.
3. **Continuity Assessment (`row_structure`):** Measures in-row distances. Rows with gaps $\ge 5\text{ m}$ are classified as `disrupted` (producing inspection targets); otherwise `regular`.
4. **Inter-Row Corridors (`interrow_area`):** Computes ground polygons between adjacent rows and strictly subtracts canopy polygons to **guarantee 0% overlap**.
5. **Ground Cover (`interrow_cover`):** Computes Excess Green index ($2G - R - B$) on ground pixels to classify `bare_soil` (<25%), `mixed` (25–75%), or `vegetation` (>75%).

---

## 6. Hardware Benchmark & Measured Performance

* **Benchmark Hardware:** Apple M5 Pro (16-core GPU, unified memory, Apple Silicon MPS).
* **Per-Tile Inference Time:** **$5.3\text{ ms}$** per $1024 \times 1024$ tile.
* **Full Orthomosaic (311 tiles):** **$\approx 1.65\text{ seconds}$** total inference time.
* **External APIs / LLMs:** **None.** All inference and spatial algorithms run 100% locally and offline.

---

## 7. Competition Deliverables

| Deliverable | Location | Description |
| :--- | :--- | :--- |
| **Route** | `route.geojson` | Valid LineString in `EPSG:32635` with `length_m`. Returns to `(629504.70, 5220250.75)` within 5 m. |
| **Measurements** | `measurements.csv` | Lengths ($m$) and areas ($m^2, ha$) by `vineyard_id` / `row_id`. |
| **Marcaj Import** | `team_upload_partX.zip` | 5 ZIP parts ($\le 90\text{ MB}$ each) containing `annotations.xml` + 311 original `.tif` tiles. |
| **Trained Weights** | [`weights/best.pt`](weights/best.pt) | Fine-tuned YOLO26-Seg model weights (23.3 MB). |
| **Web Dashboard** | Link in header | Interactive Leaflet/MapLibre map showing blocks, rows, metrics, and walking path. |

---

## 8. Licences & Attribution

* **Sireț3 UAV Imagery:** **CC BY 4.0** — Credit: *3DATA COLLECT / OpenAerialMap*, contributors to the Open Imagery Network.
* **Passages & Restrictions Vector Data:** Contains OpenStreetMap data, © OpenStreetMap contributors, **ODbL**.
* **Code:** MIT License.

