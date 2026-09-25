# Research

Part of the [Sireț3 knowledge base](../KNOWLEDGE_BASE.md). Cite [sources](sources.md).

Each path is a question to close, not a result. Status starts at `not started`. When a path produces a number, write it under Findings and point at the script, dataset licence, and date. Do not paste unverified dataset URLs into the fact files.

| ID | Question | Why it matters | Where to look | Status | Findings |
|---|---|---|---|---|---|
| R1 | Can a canopy instance model trained on Riseholme transfer to 2.5 cm Sireț3 tiles? | 25% of the score. Riseholme is the only dataset the brief says has canopy and row classes. | Riseholme paper and licence; a few local tiles including `r021_c012` and `r006_c004` as a visual check only (they are not a test set). | not started | |
| R2 | Does a row-first method (line detection, then split every 1.0–1.5 m) beat instance segmentation on touching canopies? | Rules require a split even when foliage does not narrow. | Annotation rules §2.2; classical Hough / skeleton baselines. | not started | |
| R3 | How should plants cut by a tile edge be paired so they are not double-counted in the area union? | Canopy area is the union. Edge pieces are separate polygons. | Rules §2.4; grid formula in [Spatial](spatial.md). | not started | |
| R4 | What color and texture separates vine canopy, vine tube, shadow, and weed at 2.5 cm? | Tubes and stakes are neither canopy nor waste. Shadows are not canopy. | Example previews; rules §2 and §3. | not started | |
| R5 | Which waste detector has a low false-positive rate on soil, tubes, and stones? | False boxes cost the same as misses. IoU threshold is only 0.3, but the box must be tight. | DroneWaste licence; rules §3. | not started | |
| R6 | Can `row_structure` and `interrow_cover` be rules on geometry and color instead of a classifier? | 5% of the score. Thresholds are explicit: 5 m gap; 25% and 75% cover. | Rules §4.3 and §5.2. | not started | |
| R7 | How to cluster canopies into blocks given the 5 m gap rule and the “road always splits” rule? | 2% + 2% + 2% grouping, and every object needs an id. | `passages.geojson`; rules §6. | not started | |
| R8 | What graph lets a route stay inside inter-rows ∪ passages and still reach the start? | Entire 25% route score can be 0. | `passages.geojson`, `forbidden.geojson`, `start.geojson`. | not started | |
| R9 | Is the organizer ZIP accepted by Marcaj, or must parts 1–4 be split below 90×10⁶ bytes? | Publishing is blocked if the upload fails. | Marcaj draft project; byte sizes in [Spatial](spatial.md). | not started | |
| R10 | What `measurements.csv` columns does the jury need to see? | Required file, schema unstated. | Challenge description “Counts and measurements”; Slack if a template appears. | not started | |
| R11 | UOPNOA: useful for block masks, or a distraction because it is not plant-level? | Brief warns it is not canopy ground truth. | UOPNOA licence and label spec. | not started | |
| R12 | Source mosaic at 2.40 cm vs tiles at 2.50 cm: train on source crops or on the supplied tiles only? | Domain shift and CRS (4326 vs 32635). | [Spatial](spatial.md). | not started | |

## Findings log

_Empty._

Related: [Solution](solution.md) · [Data](data.md) · [Scoring](scoring.md)
