# KNOWLEDGE BASE — Vineyard AI Field Challenge (Sireț3)

<!--
KB-RETRIEVAL
challenge: Vineyard AI Field Challenge · Deeptech GigaHack 2026 · provider Marcaj · dataset Sireț3 / Siret3
event: 25–27 September 2026 · Tekwill, Chișinău · online and offline
deadline: 2026-09-27 15:00 Europe/Chisinau (EEST, UTC+3) · repo AND Marcaj
prize: MDL 30,000 · 1 team
crs: EPSG:32635 (WGS 84 / UTM 35N, metres) for every submission geometry
tiles: 311 GeoTIFF · 2048×2048 · 0.025 m/px · 51.2 m · JPEG-in-TIFF YCbCr · names siret3_rNNN_cNNN.tif
labels: vineyard=polygon canopy · waste=axis-aligned box · row=polyline · interrow_area=polygon
attributes: vineyard_id · row_id · row_structure=regular|disrupted|unassessable · interrow_cover=bare_soil|vegetation|mixed|unassessable
start: EPSG:32635 (629504.70, 5220250.75) · 47.1230335 N, 28.7073776 E · tile siret3_r018_c010.tif
submission_root: route.geojson · measurements.csv · README.md · code · weights · web UI link
marcaj: upload all 311 BEFORE publish · 63 jobs · only submitted jobs are scored
scoring: 85% automatic + 15% engineering · hidden tile subset · annotate every tile
licence: imagery CC BY 4.0 (3DATA COLLECT / OpenAerialMap) · passages/forbidden include OSM ODbL
status: context only · no solution chosen · updated 2026-09-25
local_assets: /Users/chirill/Downloads/assets_for_participants  (NOT in this git repo)
-->

**Status:** context capture only. No model, route, or architecture has been chosen.
**Updated:** 2026-09-25.
**How to read this file:** facts are tagged with a source id from [Sources](#sources). `MEASURED` means computed from the local files on 2026-09-25, not copied from a PDF. Sections [Solution workspace](#solution-workspace) and [Research paths](#research-paths) are the only places for decisions. Do not treat them as challenge rules.

## Retrieval index

| If you need… | Go to |
|---|---|
| One-paragraph brief, deadline, prize, what “done” means | [Challenge](#challenge) |
| Exact files the jury expects in the repo | [Submission contract](#submission-contract) |
| Score weights and match rules | [Scoring](#scoring) |
| Label names, attributes, drawing rules | [Annotation spec](#annotation-spec) |
| Marcaj upload / publish / submit sequence | [Marcaj workflow](#marcaj-workflow) |
| Tile names, CRS, geotransform, grid formula | [Spatial reference](#spatial-reference) |
| What each asset folder contains | [Data catalog](#data-catalog) |
| The two worked example tiles | [Worked examples](#worked-examples) |
| PDF vs file disagreements, upload-size trap | [Conflicts and traps](#conflicts-and-traps) |
| Where a number came from | [Sources](#sources) |
| What we decided, and what we have not | [Solution workspace](#solution-workspace) |
| Experiments still to run | [Research paths](#research-paths) |
| Terms | [Glossary](#glossary) |

---

## Challenge

Deeptech GigaHack 2026, 25–27 September 2026, Tekwill, Chișinău. The challenge provider is **Marcaj** (rules, annotation platform, scoring, support). GigaHack hosts the event. Mode is online and offline. Prize is **MDL 30,000** cash for one winning team. [S-DESC]

**Problem.** Vineyard operators need a map of planting, row structure, visible waste, and places that need a walk-through. Aerial imagery alone does not give measured areas or a walking plan. Moldova’s agriculture ministry estimates 2026 vineyard maintenance at MDL 52,000–80,000 per hectare (including depreciation). A hypothetical 20 ha holding is therefore MDL 1.04–1.60 million per year. The stated benefit is less preparation and walking time while still covering the planting, including subsidy-compliance audits. The brief’s example: cutting a route from 6 km to 4.2 km is 30% less distance, or 27 minutes at 4 km/h. [S-DESC]

**Task.** Turn Sireț3 — an open, unannotated RGB orthomosaic from Moldova — into an annotated vineyard map and a walking route that a person can use. The deliverable is a neural-network model, Marcaj annotations, measurements, a route, and a working web interface. Teams may train on other open labelled vineyard data, mix ML with classical vision, then import pre-annotations into Marcaj and correct them there. [S-DESC]

**Deadline.** 15:00 Sunday 27 September 2026, Chișinău time, for both the repository link and the Marcaj project. At that time projects are frozen and organizers export the annotations. [S-DESC] [S-MARCAJ]

**Pitch.** 5 minutes plus 5 minutes of questions. Show the working web interface: map, objects, IDs, measurements, route. A laptop demo is accepted; the deployed URL goes in the README. [S-DESC]

**Support.** Challenge channel in the GigaHack Slack, Marcaj team, 09:00–23:00. Pinned clarifications apply to every team. [S-DESC] [S-MARCAJ]

**Admission (all required, or the entry is not scored for the prize).** [S-DESC]

- A working web interface.
- A published Marcaj project whose jobs are submitted.
- Correct formats and georeferencing.

Tie-break: walking-route score, then canopy segmentation, then jury vote. [S-DESC]

---

## Submission contract

One repository link. The **repository root** must contain: [S-DESC]

| Path | Contract |
|---|---|
| `route.geojson` | One `LineString` in EPSG:32635. Starts and ends at the supplied start point (5 m tolerance). Property `length_m`. |
| `measurements.csv` | Block and row counts, row lengths, and areas by `vineyard_id` / `row_id`. Shown to the jury. Numeric scores for counts and areas are computed from the Marcaj export, the same way for every team, not from this CSV. **Column schema is not specified.** |
| `README.md` | Install and run from the supplied tiles to `route.geojson` and `measurements.csv`. Pinned dependencies (Dockerfile is a plus). Where to get model weights. Processing time for the full 311-tile set and the hardware it was measured on. Any paid APIs or LLMs used. Link to the working web interface. |
| application and processing code | Reproduce the result. |
| model weights | In the repo or by link. No size limit. Compute is not provided. |

Also required in the product, not necessarily as a single file: a web UI that shows route polylines and their lengths, `vineyard_id` / `row_id`, canopy and inter-row areas, block and row counts, and individual and total row lengths. [S-DESC]

Geometries, the route, and measurement tables are EPSG:32635. GeoJSON coordinates are in that system (metres), not longitude/latitude. Areas in m² and hectares. Lengths in metres. Measurements are horizontal, with no terrain correction. [S-DESC]

Annotations themselves are taken from the team’s Marcaj project. Teams do not upload an annotation export for scoring. Export from Marcaj (for example `json_simple` or CVAT XML) is for the team’s own measurements and UI. [S-MARCAJ]

Suggested interchange: GeoJSON and CSV/JSON; **CVAT for images 1.1** for Marcaj import. Any implementation stack is allowed. [S-DESC]

---

## Scoring

85% automatic metrics, 15% expert engineering. Scoring uses a **hidden subset** of the 311 tiles, including tiles with no vineyard. Annotate all of them. Matching is one-to-one: a duplicate is a false positive; a miss stays an error. [S-DESC]

| Weight | Criterion | Rule |
|---:|---|---|
| 25% | Canopy segmentation | `0.6 ×` canopy-class IoU `+ 0.4 ×` F1 of individual canopies matched one-to-one at IoU ≥ 0.5. False canopies on tiles with no vineyard are penalised by `0.5 ×` the share of the tile they cover. |
| 10% | Waste detection | Bounding-box F1, one-to-one, IoU ≥ 0.3. Misses, false positives, and duplicates all reduce the score. |
| 15% | Axes and attributes | **8%** row-axis F1: a predicted axis and a reference axis match when each lies at least 80% within 0.4 m of the other. **5%** attributes `row_structure` and `interrow_cover`: mean of accuracy and macro-F1 over every reference object. A missing object is an attribute error, not a skip. **2%** grouping by `vineyard_id`: objects of one block share an ID; objects of different blocks do not. The ID strings need not match the reference. |
| 10% | Counts and measurements | 2% block count (distinct `vineyard_id`); 2% row count (distinct `row_id`); 2% canopy area; 2% inter-row area; 2% total row length. Each value scores `max(0, 1 − relative_error / tolerance)`. Tolerance is **15%** for counts and areas and **10%** for length. Computed from Marcaj annotations. |
| 25% | Walking route | Up to **15%** coverage of a hidden list of inspection locations and waste. A target is visited if the route passes within **2 m**. Up to **10%** efficiency `L_ref / L`, awarded only from **90%** coverage and scaled by coverage. `L_ref` is the shorter of the organizers’ route and the shortest admitted team route. The route scores **0** on this criterion if more than **2%** of its length lies outside passable inter-row areas and authorised passages, or if it does not return to the start (5 m tolerance). |
| 15% | Engineering | Architecture 5, robustness 4, scalability 3, measured performance 3. Judged from a working reproducible demo. Performance uses the README’s time and hardware; the jury may ask for a re-run. |

Weights sum to 100. [S-DESC]

---

## Annotation spec

Version 1.0, 25 September 2026. The scoring reference follows these rules exactly. Label and attribute names are **lowercase** and must match character for character. [S-RULES]

### Objects

| Label | CVAT type | What it is | Attributes |
|---|---|---|---|
| `vineyard` | polygon | Canopy of **one** grapevine, top-down. Not a row, not a block. | `vineyard_id` |
| `waste` | rectangle (axis-aligned box) | One piece of litter, or one inseparable cluster. The box area is not the waste area. | `vineyard_id` |
| `row` | polyline | Centre line of one vine row, inside this tile. | `vineyard_id`, `row_id`, `row_structure` |
| `interrow_area` | polygon | Ground between the canopies of two neighbouring rows of the same block. | `vineyard_id`, `interrow_cover` |

Allowed values: [S-RULES] [S-DESC]

- `row_structure`: `regular` · `disrupted` · `unassessable`
- `interrow_cover`: `bare_soil` · `vegetation` · `mixed` · `unassessable`

`unassessable` is a real answer. It is scored like any other value. It is used when the row or the ground cannot be made out (deep shadow, overexposure, weeds taller than the vines, canopy closed over the inter-row). [S-RULES]

ID strings are chosen by the team (`V03`, `north`, `7` are all legal). Scoring compares grouping, not the strings. Recommended pattern: block `V01`, `V02`, … and row `<vineyard_id>-R<nn>` such as `V03-R017`, numbered across the whole block. [S-RULES]

### Golden rules

1. One canopy polygon = one plant. Never one polygon over a whole row or block.
2. Grapevines only. Fruit trees, shrubs, weeds, grass, crops, and vines on fences, arbours, or houses are not `vineyard`.
3. One polyline per physical row **per tile**, from the first vine to the last vine in that tile (or to the tile edge), **through gaps**. A gap does not create a new `row_id`.
4. Canopies and inter-row polygons never overlap. The inter-row runs from canopy edge to canopy edge, not from axis to axis.
5. The same block and the same physical row keep the same `vineyard_id` and `row_id` on every tile.
6. Every tile has an answer: objects, or **No objects in this frame**. Only submitted jobs are scored. [S-RULES]

### Canopies (`vineyard`)

Trace the leaves, within about 10 cm. Exclude bare soil, the plant’s shadow, weeds, and grass. A plant that is entirely invisible in deep shadow is not drawn. A plant cut by the tile edge is traced up to the edge; the rest is a separate polygon on the neighbouring tile. A missing or dead plant is not drawn; the gap shows up in `row_structure`. [S-RULES]

Young vines: each plant is its own polygon, however small. Leaf clumps under about 0.2 m² that are not part of a plant are not annotated. White protective tubes and stakes are part of the planting: neither canopy nor waste. The rules’ example of this case is rows about 2.7 m apart on tilled soil. [S-RULES]

Older vines with touching canopies: split where the foliage visibly narrows. If there is no narrowing, split at the in-row planting distance, measured from trunks, stakes, or gaps in the same row, **typically 1.0–1.5 m**. [S-RULES]

Not a vineyard: orchard crowns (about 2–4 m wide, round, 4–6 m apart). Vines are under about 1 m wide and planted every 1.0–1.5 m along the row. A tree standing inside a vineyard is not a canopy; vines around it are annotated as usual. Garden vineyards on the village edge are annotated only if the vines stand in **at least three rows**. A single vine or an arbour in a yard is not. [S-RULES]

### Waste (`waste`)

A tight axis-aligned box around clearly visible litter, anywhere on the tile (vineyard and surrounding land). Separate items get separate boxes. Pieces that overlap and cannot be told apart get one box. [S-RULES]

| Waste | Not waste |
|---|---|
| bags, plastic sheets and film, bottles, cans, packaging, tyres, construction debris, heaps of rubbish | vine tubes, stakes, trellis posts and wires, irrigation hoses, stones, bare or pale soil, flowering shrubs, pruning residue and cut branches, vehicles and machinery |

`vineyard_id`: the block the object lies in, or the nearest block within 10 m. Farther than that, leave `vineyard_id` empty. When unsure, leave it out: a false box costs as much as a miss. [S-RULES]

The two example tiles contain **zero** waste objects. There is no `<box>` sample in the example XML. [S-EX]

### Row axes (`row`)

One polyline per physical row per tile. Keep the line within **0.2 m** of the vine centres. A straight row may be two points; add points where a row bends. The outermost rows of a block are included. Gaps do not split the row. The same physical row on two tiles is two polylines with one `row_id`. [S-RULES]

Scoring tolerance is looser than the drawing rule: 0.4 m and 80% mutual coverage. [S-DESC] [S-RULES]

`row_structure` describes **this tile only**. The same row may be `regular` on one tile and `disrupted` on the next. [S-RULES]

| Value | When |
|---|---|
| `regular` | No gap of 5 m or more along the row in this tile. |
| `disrupted` | A visible gap of 5 m or more in this tile: several missing or dead vines, or a tree or obstacle in the row. |
| `unassessable` | The row cannot be made out over most of its length in this tile. |

Rows and inter-row areas stop at the edge of the planting. A dirt road is not part of the block. There is no inter-row outside the outermost rows. [S-RULES]

### Inter-row areas (`interrow_area`)

One polygon per inter-row per tile, cut at the tile edge. Long sides follow canopy edges. Short sides stop where the rows end: headland, roads, and exterior land are excluded. If one row is shorter, end at the shorter one. Cut out trees and buildings that stand in the inter-row. This polygon is the walkable ground the route uses, and its area is scored. [S-RULES]

| `interrow_cover` | When |
|---|---|
| `bare_soil` | Vegetation covers less than about a quarter. |
| `mixed` | About a quarter to three quarters (strips of grass/weeds alternating with soil). |
| `vegetation` | Grass or weeds cover more than about three quarters. |
| `unassessable` | Ground cannot be seen. |

Judge each inter-row on its own, inside this tile. [S-RULES]

### Blocks (`vineyard_id`)

A block is a connected planting. Two plantings are the same block when they touch or are separated by **less than 5 m** of non-vineyard ground. **A road or a track always separates blocks.** Every canopy, row, inter-row, and waste within 10 m carries that block’s id. Distinct `vineyard_id` values are the block count. Distinct `row_id` values are the row count. A row redrawn with a new id on the next tile is counted twice. [S-RULES]

### Worked ID example from the rules (not the scored examples)

Block `V03` crosses `siret3_r021_c012` and `siret3_r021_c013`. Three rows, each drawn on both tiles with the same `row_id`. `V03-R02` has a 7 m gap only on the right tile, so that tile’s polyline is `disrupted` and the left tile’s is `regular`. Result: 1 block, 3 rows, 45 canopies (24 + 21). Naming the right tile `R04`–`R06` would wrongly count 6 rows. [S-RULES]

### Do not put these in Marcaj

Inter-row centre lines. Roads, tracks, the supplied passages, forbidden zones, and the start point. Inspection targets (they belong in the application output). Orchards, trees, shrubs, buildings, fences, non-grape crops. Anything in the black area outside the imagery on edge tiles. [S-RULES]

### Attribute mistakes that change the score

| Mistake | Effect |
|---|---|
| Renumber rows from 1 on every tile | One physical row counts as many. |
| New `vineyard_id` for the same block on each tile | Block count and grouping score drop. |
| Empty `row_structure`, `interrow_cover`, or `vineyard_id` | Wrong answer, or the object belongs to no block. |
| `Regular`, `bare soil`, `grass` | Not an allowed value. Use the exact lowercase token. |
| `interrow_cover` on a row, or `row_structure` on an inter-row | Ignored. |

[S-RULES]

### Pixel annotation vs metres

Annotate in pixels in Marcaj. The platform keeps the georeferencing and scoring converts to metres. Tiles are 2048 × 2048 px, 2.5 cm/px, 51.2 m on the ground, EPSG:32635. [S-RULES]

CVAT image coordinates: origin at the top-left, `x` to the right, `y` downward. Confirmed by the example polylines, which run to `x = 2048` and `y = 0` or `y = 2048`. [S-EX]

---

## Marcaj workflow

Accounts are created from the team list and emailed on Friday evening (“Your Marcaj account”: address, email, generated password). No sign-up. Check spam. Language can be EN / RO / RU. The team project starts in **Draft** with the four labels already configured. Every member can upload, publish, annotate, review, and export. Agree who publishes. [S-MARCAJ] [S-DESC]

### Upload ZIP (CVAT for images 1.1)

```text
team_upload.zip
├── annotations.xml
└── images/
    └── siret3_r021_c012.tif    # supplied file, unchanged, original name
```

- Each ZIP ≤ 90 MB. One ZIP per supplied part is the intended pattern. [S-MARCAJ] [S-RULES]
- JPEG/PNG are rejected: they have no georeferencing. [S-DESC]
- Tiles may be uploaded with no `annotations.xml` if there is no model yet. [S-MARCAJ]
- Pre-annotations import **only before publish**, and only together with the tiles. [S-DESC]
- Until publish, **Remove all** clears the project so a part can be re-imported. [S-MARCAJ]
- After a ZIP imports, read the report. Skipped files or dropped objects mean a renamed tile or a typo in a label or attribute. A note that a class was “added from the label dictionary” is normal when that ZIP has no objects of that label (often `waste`). [S-MARCAJ]
- Upload parts one by one. Wait for each report. The Data card must show **311 files**. Then publish. [S-MARCAJ]
- Publish creates jobs of 5 tiles: **63 jobs** (62 × 5 + one job of 1). [S-MARCAJ]
- After publish: no new pre-annotations, and do not delete, add, or rename tiles, and do not edit labels. [S-DESC] [S-MARCAJ]

### Editor (after publish)

Start labeling assigns the next free job of five tiles. Two people never receive the same job. A job stays with that person until submit. [S-MARCAJ]

| Action | Control |
|---|---|
| Select | Click the shape or the Objects list |
| Attributes | Text for IDs; drop-down for `row_structure` and `interrow_cover` |
| Canopy or inter-row | Polygon `P`, close on the first point |
| Row | Polyline `L`, double-click to finish |
| Waste | Rectangle `R` |
| Edit vertices | Pointer `V` |
| Delete | Delete or bin |
| Undo / redo | Ctrl+Z / Ctrl+Y |
| Zoom | Wheel, or − / + / Fit |
| Hide tags | Tag icon (needed when hundreds of canopies cover the image) |
| Previous / next tile | `D` / `F` (tile saves on step) |
| Pick label | `1`–`9` |
| Empty tile | Tick **No objects in this frame** |
| Submit | On the last tile, Submit (`Enter`) |

Shortcuts do not fire while an attribute field is focused. A job cannot be submitted while any of its tiles has no answer. [S-MARCAJ]

Quick-start screenshot colors in the editor: canopies green, row axes blue, inter-row areas orange. Those are UI colors, not the example-preview colors. [S-MARCAJ]

Submitted jobs show as **In review**. Review is optional. Sending a job back makes it in progress again and **unscored** until resubmit. Near the deadline, fix and resubmit rather than send back. [S-MARCAJ]

**Before 15:00 Sunday:** In progress = 0. Every job is In review or Approved. Nothing sent back and left unsubmitted. Repository link submitted. [S-MARCAJ]

### Three failures that zero out work

1. Publishing before all five parts are in. Missing tiles cannot be pre-annotated afterwards.
2. Jobs left in progress at the deadline. They count as unannotated.
3. Deleting or renaming tiles, editing labels, or deleting the project. Matching is by file name and label name. [S-MARCAJ]

Assign IDs on the whole mosaic **before** cutting annotations per tile. Neighbouring tiles should be corrected by the same person. File names are `siret3_r<row>_c<column>` and the ZIPs are in name order. [S-RULES] [S-MARCAJ]

### Exact `annotations.xml` shape

The example file is CVAT for images 1.1 (`<version>1.1</version>`). Shapes use `source="manual"`, `occluded="0"`, `z_order="0"`. Points are `x,y;x,y` in pixel coordinates. Polygons are not closed by repeating the first point. [S-EX]

Label block to copy (attributes `mutable=False` in the example; the rules’ appendix omits `mutable` and empty defaults — follow the example file, which is a known-good upload): [S-EX] [S-RULES]

```xml
<annotations>
  <version>1.1</version>
  <meta><task><labels>
    <label><name>vineyard</name><type>polygon</type>
      <attributes><attribute><name>vineyard_id</name><input_type>text</input_type></attribute></attributes></label>
    <label><name>waste</name><type>rectangle</type>
      <attributes><attribute><name>vineyard_id</name><input_type>text</input_type></attribute></attributes></label>
    <label><name>row</name><type>polyline</type>
      <attributes>
        <attribute><name>vineyard_id</name><input_type>text</input_type></attribute>
        <attribute><name>row_id</name><input_type>text</input_type></attribute>
        <attribute><name>row_structure</name><input_type>select</input_type>
          <values>regular
disrupted
unassessable</values></attribute>
      </attributes></label>
    <label><name>interrow_area</name><type>polygon</type>
      <attributes>
        <attribute><name>vineyard_id</name><input_type>text</input_type></attribute>
        <attribute><name>interrow_cover</name><input_type>select</input_type>
          <values>bare_soil
vegetation
mixed
unassessable</values></attribute>
      </attributes></label>
  </labels></task></meta>
  <image id="0" name="siret3_r021_c012.tif" width="2048" height="2048">
    <polyline label="row" points="..." occluded="0" z_order="0">
      <attribute name="vineyard_id">V01</attribute>
      <attribute name="row_id">V01-R01</attribute>
      <attribute name="row_structure">regular</attribute>
    </polyline>
    <polygon label="interrow_area" points="..." occluded="0" z_order="0">...</polygon>
    <polygon label="vineyard" points="..." occluded="0" z_order="0">...</polygon>
    <!-- waste: no sample in the example ZIP. CVAT 1.1 rectangles are <box xtl="" ytl="" xbr="" ybr="">.
         Confirm against a Marcaj import before relying on it. -->
  </image>
</annotations>
```

The rules’ own polyline snippet: [S-RULES]

```xml
<polyline label="row" points="112.0,1830.5;1990.4,402.7" occluded="0">
  <attribute name="vineyard_id">V03</attribute>
  <attribute name="row_id">V03-R02</attribute>
  <attribute name="row_structure">disrupted</attribute>
</polyline>
```

---

## Spatial reference

### Challenge tiles (the surface that is scored)

| Property | Value | Source |
|---|---|---|
| Count | 311 unique names | MEASURED [S-GEO] |
| File name | `siret3_r{row:03d}_c{col:03d}.tif` | [S-README] |
| Size | 2048 × 2048 px | [S-README] [S-GEO] |
| Ground sample distance | 0.025 m/px | [S-README] [S-GEO] |
| Ground size | 51.2 m × 51.2 m | [S-README] |
| CRS | EPSG:32635 | [S-README] [S-GEO] |
| Raster type | PixelIsArea. Tiepoint is the upper-left corner of pixel (0,0), not the centre. | MEASURED GeoKey 1025 = 1 [S-GEO] |
| Compression | JPEG-in-TIFF (compression 7), photometric YCbCr (6), subsampling 2×2, 8-bit, 3 bands, internal tiles 256×256 | MEASURED [S-GEO] |
| Nodata | Edge tiles include black outside the flight footprint. Do not annotate it. | [S-RULES] |

**Grid.** Rows increase south. Columns increase east. Tiles do not overlap. The study-area polygon area equals `311 × 51.2² = 815,267.84 m² = 81.527 ha`. [S-GEO]

Upper-left corner of tile `r`, `c` in EPSG:32635 metres (verified on five tiles, max error 0): [S-GEO]

```text
X_ul = 628992.0 + c * 51.2
Y_ul = 5221222.4 - r * 51.2
X_lr = X_ul + 51.2
Y_lr = Y_ul - 51.2
```

Pixel corner `(px, py)` to map metres (pixel-is-area, `py` downward):

```text
E = X_ul + px * 0.025
N = Y_ul - py * 0.025
```

Half a pixel is 1.25 cm. That is small next to the 0.4 m axis tolerance and the 2 m route tolerance. Whether Marcaj treats a CVAT point as a pixel corner or a pixel centre is not stated.

Row index runs 5–39 (35 distinct rows). Column index runs 0–33 (34 distinct columns). There is no `r000`–`r004` in the package; the indices sit on this virtual grid. [S-GEO]

Intentional holes inside the row/column bounding box (these tiles were not supplied): [S-GEO]

| Row | Missing columns |
|---|---|
| 25 | 20–30 |
| 26 | 23–28 |
| 27 | 28 |

Per-row column span (inclusive, after those holes): [S-GEO]

| Row | Cols | n | Row | Cols | n | Row | Cols | n |
|---|---|---:|---|---|---:|---|---|---:|
| 5 | 4–4 | 1 | 17 | 6–12 | 7 | 29 | 15–33 | 19 |
| 6 | 2–4 | 3 | 18 | 7–13 | 7 | 30 | 16–32 | 17 |
| 7 | 1–4 | 4 | 19 | 8–14 | 7 | 31 | 17–31 | 15 |
| 8 | 0–5 | 6 | 20 | 8–15 | 8 | 32 | 18–30 | 13 |
| 9 | 0–6 | 7 | 21 | 9–16 | 8 | 33 | 18–30 | 13 |
| 10 | 0–6 | 7 | 22 | 10–17 | 8 | 34 | 19–29 | 11 |
| 11 | 1–8 | 8 | 23 | 10–17 | 8 | 35 | 20–28 | 9 |
| 12 | 2–9 | 8 | 24 | 11–18 | 8 | 36 | 21–27 | 7 |
| 13 | 3–9 | 7 | 25 | 12–19 and 31–31 | 9 | 37 | 22–26 | 5 |
| 14 | 4–10 | 7 | 26 | 13–22 and 29–32 | 14 | 38 | 22–25 | 4 |
| 15 | 4–11 | 8 | 27 | 13–27 and 29–33 | 20 | 39 | 23–23 | 1 |
| 16 | 5–11 | 7 | 28 | 14–33 | 20 | | | |

ZIP membership (name order, uncompressed sizes are almost equal to the zip size because the TIFFs are already JPEG): [S-GEO]

| Part | Files | First | Last | Bytes |
|---|---:|---|---|---:|
| part1of5 | 74 | `siret3_r005_c004.tif` | `siret3_r017_c006.tif` | 93,823,066 |
| part2of5 | 71 | `siret3_r017_c007.tif` | `siret3_r026_c014.tif` | 93,624,576 |
| part3of5 | 78 | `siret3_r026_c015.tif` | `siret3_r030_c022.tif` | 93,207,449 |
| part4of5 | 76 | `siret3_r030_c023.tif` | `siret3_r036_c025.tif` | 94,108,721 |
| part5of5 | 12 | `siret3_r036_c026.tif` | `siret3_r039_c023.tif` | 10,414,422 |

Tile file size ranges from 0.15 MB to 1.66 MB (median 1.37 MB). Small files are edge tiles with a lot of black. [S-GEO]

Study-area bounding box, EPSG:32635: X 628,992.0 – 630,732.8 (1,740.8 m), Y 5,219,174.4 – 5,220,966.4 (1,792.0 m). The polygon has 145 vertices and no holes. [S-GEO]

### Start / finish

| Field | Value |
|---|---|
| Name | START |
| Role | Route start **and** finish |
| Description | Dirt-road junction at the north-west corner of the vineyard block |
| EPSG:32635 | X = 629,504.70 , Y = 5,220,250.75 |
| WGS84 | 47.1230335 N , 28.7073776 E |
| Tile | `siret3_r018_c010.tif` |
| Position in that tile | about 0.70 m / 28 px from the west edge, about 50.05 m / 2002 px from the north edge (near the south edge) |

[S-README] [S-GEO] from `start.geojson`.

That point lies inside the source orthomosaic footprint. [S-GEO]

### Passages and forbidden zones

Both files are a single `FeatureCollection` with one feature, CRS `urn:ogc:def:crs:EPSG::32635`, geometry `MultiPolygon`. [S-GEO]

| File | `properties.type` | `properties.source` | Parts | Area |
|---|---|---|---:|---|
| `passages.geojson` | `passage` | “OpenStreetMap highways, buffered; plus 5 passages digitised from the orthomosaic (`work/manual_passages.json`)” | 2 polygons, 13 holes | 40,000 m² (4.00 ha) |
| `forbidden.geojson` | `forbidden` | “village core outside the study area; OSM buildings (+1 m); commercial/religious compounds” | 19 polygons, no holes | 744,927 m² (74.49 ha), of which one part is 74.02 ha |

[S-GEO] [S-README]

The passage buffer width is not stated. Do not invent a centre-line from the area. The route may use these polygons plus passable inter-row areas. It may not cross canopies, fences, or forbidden polygons. More than 2% of route length outside the allowed surfaces scores 0 for the route criterion. [S-DESC] [S-RULES]

The overview and the passage preview show the same rotated flight: vineyards on the west and south, a dense village on the northeast, roads between them. The start marker sits on a track junction at the north-west corner of a vineyard block. Forbidden cover sits mainly on the village. Magenta corridors follow roads, tracks, and some headlands. Preview colors are not the Marcaj label colors. [S-PREVIEW] [S-README]

### Source orthomosaic (training only)

`04_source/siret3_source_orthomosaic_EPSG4326.tif`. [S-README]

| Property | Measured from the file [S-GEO] | Stated in the PDF [S-DESC] [S-README] |
|---|---|---|
| Container | BigTIFF, 658,583,344 bytes (~628 MiB; README says 659 MB) | 659 MB |
| CRS | EPSG:4326 (geographic). GeoKey 1024 = 2. | EPSG:4326 |
| Size | 70,246 × 81,986 px | not stated |
| Pixel scale | 3.16481e-7 ° lon × 2.16017e-7 ° lat ≈ **0.0240 m** on both axes at the mosaic centre | **3.52 cm/px** |
| Upper left | lon 28.7009351352 , lat 47.1312466746 | not stated |
| Lower right | lon 28.7231666595 , lat 47.1135363048 | not stated |
| Footprint box | about 1,687 m × 1,969 m ≈ 332 ha | not stated |
| Valid pixels | GDAL `STATISTICS_VALID_PERCENT` = 43.59% (per band) | not stated |
| Implied valid area at 2.40 cm | about **145 ha** | “~145 ha” |
| Capture | not in the TIFF tags that were read | 20 May 2025, UAV, RGB, unannotated |
| Provider | not in the TIFF | 3DATA COLLECT, via OpenAerialMap |
| Compression | JPEG-in-TIFF, YCbCr, 2×2 subsampling, internal tiles 512×512, 8-bit RGB | RGB |

Use the **tile** geotransform (2.5 cm, EPSG:32635) for anything that is scored. The source file is for training on the whole survey. The PDF’s 3.52 cm/px does not reproduce the ~145 ha figure; the measured 2.40 cm GSD does. See [Conflicts and traps](#conflicts-and-traps).

GDAL metadata on the source also says `UNITTYPE` = metre on the byte samples. That is a sample-unit tag, not the CRS. Coordinates in this file are degrees. [S-GEO]

A public OpenAerialMap item URL was **not** found while writing this file. The package says the mosaic is the one published on OpenAerialMap. [S-README]

---

## Data catalog

Local path (not committed): `/Users/chirill/Downloads/assets_for_participants`. [S-README]

| Folder | File | Role |
|---|---|---|
| `01_tiles/` | `siret3_challenge_tiles_part1of5.zip` … `part5of5.zip` | The 311 challenge tiles. |
| `01_tiles/` | `overview.png` | ~1 m/px overview. Challenge tiles outlined, route START marked. |
| `02_route/` | `start.geojson` | Start and finish point. |
| `02_route/` | `passages.geojson` | Authorised passages. `type=passage`. |
| `02_route/` | `forbidden.geojson` | Forbidden zones. `type=forbidden`. |
| `02_route/` | `study_area.geojson` | Outline of the 311 tiles. Property `name` = “study area, 311 tiles”. |
| `02_route/` | `preview_passages_forbidden.png` | Preview of passages and forbidden zones. |
| `03_docs/` | `Vineyard_AI_Field_Challenge_description.pdf` | Tasks, submission, rules, scoring. 5 pages. |
| `03_docs/` | `Vineyard_AI_annotation_rules.pdf` | Labels, attributes, cases. v1.0, 8 pages. |
| `03_docs/` | `Marcaj_quick_start_for_teams.pdf` | Sign-in through submit. v1.0, 6 pages. |
| `04_source/` | `siret3_source_orthomosaic_EPSG4326.tif` | Full original mosaic. Training only. |
| `05_examples/` | `siret3_examples_cvat.zip` | Two annotated tiles in the upload format. **Not scored.** |
| `05_examples/` | `preview_siret3_r021_c012.jpg`, `preview_siret3_r006_c004.jpg` | Preview renders of those annotations. |
| package root | `README.md` | Index of the package. |

### Not in the package

No trained weights. No labelled Sireț3 set beyond the two unscored examples. No waste example. No `measurements.csv` template. No sample `route.geojson`. No Marcaj credentials. No formal CSV column list. No inspection-target layer (that list is hidden and used only for scoring). No stated passage buffer width.

### Rules that constrain training data

Allowed: any open pretrained model (the brief names SAM and YOLO as examples), open datasets whose licences were checked, libraries, classical vision. Paid APIs and LLMs are allowed if the result stays reproducible and the README lists them. [S-DESC]

Manual annotation of **Sireț3** happens only in Marcaj. Annotating other datasets for training is unrestricted. The orthomosaic may be retiled any way for training. The submission is the annotation of the **supplied** tiles. Using another team’s annotations is not allowed. [S-DESC]

Named open datasets (names and counts are from the brief): [S-DESC] Licences and downloads were checked on 2026-09-25 and written under [Research paths](#research-paths).

| Dataset | What the brief says | What it is not |
|---|---|---|
| Riseholme | 855 UAV RGB images, 40,215 COCO segmentation annotations, including canopy and row classes | Not Sireț3. Scale, season, and appearance differ. |
| UOPNOA | About 34,000 RGB aerial images and land-use masks | Vineyard-block labels are not individual-canopy ground truth. |
| DroneWaste | An open annotated aerial-waste reference | Not this site. |

### Licence

Sireț3 imagery: **CC BY 4.0**. Credit 3DATA COLLECT / OpenAerialMap, contributors to the Open Imagery Network. Challenge tiles are that mosaic, reprojected to EPSG:32635 and cut. Keep the attribution when the imagery is reused. [S-README]

Route layers contain OpenStreetMap data, © OpenStreetMap contributors, ODbL. [S-README]

---

## Worked examples

Both tiles are in `05_examples/siret3_examples_cvat.zip` (`annotations.xml` + the two original GeoTIFFs). They are a format template and a visual standard. They are not part of the score. Block ids `V01` and `V02` are local to these files, not a global map of the site. [S-README] [S-EX]

Preview colors (JPG only): row axes red, disrupted rows magenta, canopies green, inter-row areas cyan. [S-README]

| Tile | Block | Rows | Canopies | Inter-rows | Waste |
|---|---|---|---:|---|---:|
| `siret3_r021_c012.tif` | `V01` | 25, all `regular`, ids `V01-R01`…`V01-R25` | 399 polygons, 4–58 points (median 14) | 24, all `bare_soil` (22 quads, 2 with 5 points) | 0 |
| `siret3_r006_c004.tif` | `V02` | 26: 21 `regular`, 5 `disrupted`, ids `V02-R01`…`V02-R26` | 251 polygons, 5–148 points (median 15) | 25: 21 `bare_soil`, 4 `mixed` | 0 |

Every shape in the example XML is `source=manual`, `occluded=0`, `z_order=0`. Every example row polyline has exactly two points. [S-EX]

What the tiles show, in the README’s words: `r021_c012` is young vines on tilled soil, one polygon per plant. `r006_c004` is sparse rows with long gaps, grass strips in the inter-rows, and white vine tubes and stakes that are not waste. [S-README]

**Observation, not a rule.** On `V01`, consecutive axis polylines are parallel and about **2.65 m** apart (perpendicular distance in pixel space × 0.025 m). The rules separately say young-vine rows are about 2.7 m apart. On this tile the rows run diagonally in image space, roughly north-northwest to south-southeast in EPSG:32635. Other blocks on the mosaic may differ. Do not hard-code this azimuth for the whole site. [S-EX] [S-RULES] [S-GEO]

---

## Conflicts and traps

Recorded so later edits do not “fix” a file to match a sentence, or the reverse, without noticing.

| Topic | Documents say | Files show | Use this |
|---|---|---|---|
| Source GSD | 3.52 cm/px [S-DESC] | ModelPixelScale ≈ 2.40 cm/px; 43.59% valid pixels × that GSD ≈ 145 ha, which matches the stated area [S-GEO] | Trust the GeoTIFF for geometry. Treat 3.52 cm as an unverified statement. |
| Challenge-tile GSD | 0.025 m/px [S-README] [S-RULES] | ModelPixelScale 0.025, 0.025 [S-GEO] | 2.5 cm. Tiles were resampled when reprojected; they are not the source GSD. |
| Upload size | “under 90 MB” / “at most 90 MB” [S-MARCAJ] [S-RULES]; README also says the five ZIPs are “at most 94 MB” [S-README] | Parts 1–4 are 93.2–94.1 × 10⁶ bytes, which is over 90 decimal MB and under 90 MiB. Part 5 is 10.4 × 10⁶ bytes [S-GEO] | If Marcaj rejects a part, split that ZIP. Do not recompress or rename the TIFFs. |
| Canopy label | Prose says “canopies”; the label is `vineyard` [S-DESC] [S-RULES] | Example polygons are `label="vineyard"` [S-EX] | The XML/Marcaj name is `vineyard`. |
| Editor vs preview colors | Quick-start: green / blue / orange [S-MARCAJ]. README previews: green / red / magenta / cyan [S-README] | Two different renders | Colors are not data. |
| Waste XML | Label type `rectangle` [S-RULES] | No `<box>` in the example [S-EX] | Confirm the box tag on a draft import. |
| `measurements.csv` | Required, described in one sentence [S-DESC] | No template | Scoring of the numbers uses Marcaj. The CSV is what the jury reads. Design columns, then record them in the README. |
| Source `UNITTYPE` | — | GDAL metadata says metre [S-GEO] | CRS is EPSG:4326 degrees. |

Operational traps already stated by the organizers, repeated because they are easy to miss: publishing early; unsubmitted jobs; renamed tiles; IDs restarted on each tile; annotating Sireț3 outside Marcaj; false canopies on empty tiles; a route that cuts through canopies or forbidden ground. [S-DESC] [S-MARCAJ] [S-RULES]

---

## Inspection targets and the route

These are application outputs. They are not Marcaj labels. [S-RULES]

Targets are locations that need inspection (visible row gaps, possibly missing planting) and detected waste. Each inspection location needs an id, coordinates, and links to `vineyard_id` / `row_id`. [S-DESC]

The route: [S-DESC] [S-RULES]

- Starts and ends at the supplied point (5 m).
- Walks on inter-row polygons and authorised passages.
- Does not cross canopies, fences, or forbidden zones.
- Visits every reachable target.
- Prefers a shorter length.
- A hidden target counts as visited within 2 m.
- Efficiency is scored only once coverage is at least 90%.
- More than 2% of length off the allowed surfaces scores 0 for the whole route criterion.

Roads separate blocks, so the passage polygons are the intended way to move between blocks and along headlands. Inter-row polygons stop at the row ends, so the route has to leave them through a passage to reach the next block or to return to the start. [S-RULES] [S-DESC]

---

## Solution workspace

Everything below this heading is **ours**. It is not a rule. Leave a dated note when a decision changes. Do not delete rejected options; move them to the log.

### Current decision

_None. Context only, 2026-09-25._

### Product skeleton (fill in)

| Piece | Choice | Why | Status |
|---|---|---|---|
| Canopy instances | | | open |
| Waste boxes | | | open |
| Row axes | | | open |
| Inter-row polygons | | | open |
| `row_structure` / `interrow_cover` | | | open |
| Block and row IDs across tiles | | | open |
| Route graph and solver | | | open |
| Web map | | | open |
| Measurement export | | | open |
| Marcaj ZIP writer | | | open |

### Pipeline (intended order, not a design)

1. Read the 311 tiles with a GeoTIFF reader that understands JPEG-in-TIFF YCbCr (GDAL/rasterio). Do not treat them as plain JPEG.
2. Predict canopies, waste, and row geometry in pixel space.
3. Stitch IDs in map space with the grid formula above.
4. Derive inter-row polygons from canopy edges and row axes. Classify cover and structure.
5. Write CVAT 1.1 ZIPs that contain the **original** TIFF bytes.
6. Import, publish, correct, submit in Marcaj.
7. Export annotations, compute measurements in EPSG:32635, build inspection targets, solve the route, write `route.geojson` and `measurements.csv`, show them on the web map.

### Open decisions

| ID | Question | Blocks |
|---|---|---|
| D1 | Segment canopies directly, or detect row lines first and then split plants along the row? | 25% of the score is canopy IoU + instance F1 |
| D2 | Which open weights are legal and close enough to 2.5 cm nadir vines? | Licence must be checked and listed |
| D3 | How are empty tiles detected so we do not paint false canopies? | Hidden non-vineyard tiles are penalised by coverage |
| D4 | Geometric inter-rows from axes, or a second segmentation? | Inter-rows must not overlap canopies and must stop at row ends |
| D5 | What is the walk graph: inter-row centre lines plus passage skeleton? | Route is 25% and fails entirely if >2% is off-network |
| D6 | CSV columns | Jury-facing; not specified |

### Decision log

| Date | Decision | Reason | Supersedes |
|---|---|---|---|
| 2026-09-25 | Capture challenge context in this file before choosing a model. | Assets and PDFs had no single index. | — |

---

## Research paths

Each path is a question to close, not a result. Status starts at `not started`. When a path produces a number, write it under Findings and point at the script, dataset licence, and date. Do not paste unverified dataset URLs into the fact sections above.

| ID | Question | Why it matters | Where to look | Status | Findings |
|---|---|---|---|---|---|
| R1 | Can a canopy instance model trained on Riseholme transfer to 2.5 cm Sireț3 tiles? | 25% of the score. Riseholme is the only dataset the brief says has canopy and row classes. | Riseholme paper and licence; a few local tiles including `r021_c012` and `r006_c004` as a visual check only (they are not a test set). | licence checked, transfer not tested | Official COCO set is CC BY 4.0, 3.3 GB. Classes are `pole`, `trunk`, `vine_row`, `vineyard`. The record does not say a `vineyard` polygon is one plant, and it does not state GSD. See findings. |
| R2 | Does a row-first method (line detection, then split every 1.0–1.5 m) beat instance segmentation on touching canopies? | Rules require a split even when foliage does not narrow. | Annotation rules §2.2; classical Hough / skeleton baselines. | not started | |
| R3 | How should plants cut by a tile edge be paired so they are not double-counted in the area union? | Canopy area is the union. Edge pieces are separate polygons. | Rules §2.4; grid formula. | not started | |
| R4 | What color and texture separates vine canopy, vine tube, shadow, and weed at 2.5 cm? | Tubes and stakes are neither canopy nor waste. Shadows are not canopy. | Example previews; rules §2 and §3. | not started | |
| R5 | Which waste detector has a low false-positive rate on soil, tubes, and stones? | False boxes cost the same as misses. IoU threshold is only 0.3, but the box must be tight. | DroneWaste licence; rules §3. | licence checked, detector not tested | DroneWaste is CC BY 4.0 but labels landfill dumps. UAVVaste is the closer open litter set (CC BY 4.0, low-altitude boxes). Neither is vineyard soil. See findings. |
| R6 | Can `row_structure` and `interrow_cover` be rules on geometry and color instead of a classifier? | 5% of the score. Thresholds are explicit: 5 m gap; 25% and 75% cover. | Rules §4.3 and §5.2. | not started | |
| R7 | How to cluster canopies into blocks given the 5 m gap rule and the “road always splits” rule? | 2% + 2% + 2% grouping, and every object needs an id. | `passages.geojson`; rules §6. | not started | |
| R8 | What graph lets a route stay inside inter-rows ∪ passages and still reach the start? | Entire 25% route score can be 0. | `passages.geojson`, `forbidden.geojson`, `start.geojson`. | not started | |
| R9 | Is the organizer ZIP accepted by Marcaj, or must parts 1–4 be split below 90×10⁶ bytes? | Publishing is blocked if the upload fails. | Marcaj draft project; byte sizes in this file. | not started | |
| R10 | What `measurements.csv` columns does the jury need to see? | Required file, schema unstated. | Challenge description “Counts and measurements”; Slack if a template appears. | not started | |
| R11 | UOPNOA: useful for block masks, or a distraction because it is not plant-level? | Brief warns it is not canopy ground truth. | UOPNOA licence and label spec. | closed: skip for canopy | CC BY 4.0, 33,699 tiles, 0.25 m/px. Class `VI` is a SIGPAC plot mask. Not plant-level. See findings. |
| R12 | Source mosaic at 2.40 cm vs tiles at 2.50 cm: train on source crops or on the supplied tiles only? | Domain shift and CRS (4326 vs 32635). | This file, Spatial reference. | not started | |

### Findings log

**2026-09-25 — labeled sets that match the four Marcaj tasks.** Sources opened that day: [S-RISE] [S-AGRIDS] [S-WASTE] [S-UAVV] [S-UOP] [S-BARROS] [S-ESCA].

| Task | Use | Do not use |
|---|---|---|
| Canopy instances (`vineyard`) | Riseholme COCO, class `vineyard`, plus `trunk` as the plant-level point. [S-RISE] | AGRIDS and the Kaggle YOLO mirror (non-commercial / no-derivatives). [S-AGRIDS] UOPNOA plot masks. [S-UOP] Ground-level bunch sets (WGISD, VINEPICs, Grapevine-Seg). |
| Row axes | Riseholme class `vine_row` is an instance mask. A centre line has to be derived. [S-RISE] | AGRIDS row labels, same licence block. [S-AGRIDS] |
| Waste boxes | UAVVaste: 772 images, 3,718 litter boxes and masks, one class, low altitude. [S-UAVV] | DroneWaste: 4,993 tiles and 5,135 boxes of landfill materials, 20 classes. Legal, wrong scene. [S-WASTE] |
| `row_structure`, `interrow_cover` | No public set uses these values. The thresholds are in the rules (5 m gap; about 25% and 75% vegetation). | — |

Riseholme record, verbatim classes: `pole`, `trunk`, `vine_row`, `vineyard` (canopy). 855 images, 40,215 COCO annotations, three seasons, train/val/test already split. File `riseholme-vineyard.zip`, 3,344,879,865 bytes. Licence on the Zenodo record: CC BY 4.0. The record does not state GSD and does not say one `vineyard` polygon equals one plant. [S-RISE]

Related AGRIDS zip is CC BY-NC-ND 4.0 (`vineyard_segmentation.v11i.yolov11.zip`, 2,224,959,050 bytes). Posts and rows at 12 m, 20 m, 30 m (Lincoln) and 40 m (Oxfordshire). Do not train the prize model on it. [S-AGRIDS]

UOPNOA: CC BY 4.0, `UOPNOA.zip` 3.8 GB, 33,699 images of 256×256 from Spanish PNOA, GSD 0.25 m/px. Class `VI` is vineyard land use from SIGPAC, 1,759 plots. That is a block-scale mask at ten times the Sireț3 pixel size. [S-UOP]

Barros et al. RGB orthomosaics are the closest published GSD: 1.7 cm/px at Esac (120 m AGL) and 1.0 cm/px at Valdoeiro and Quinta de Baixo (60 m). Masks are one semantic class, vine pixels. Only Esac is fully labeled. The GitHub code is MIT. The imagery is not a direct download; the README says to email the author. Imagery licence is not stated. [S-BARROS]

EscaYard is CC BY 4.0 and has RTK trunk locations, not canopy polygons. Flown at 30 m. The orthomosaics are multispectral and large (about 3.4 GB and 1.5 GB). [S-ESCA]

No opened dataset contains one-plant nadir canopy polygons in the Marcaj sense, inter-row polygons, or the attribute vocabularies.

---

## Sources

Cite these ids in later notes. If a later Slack pin contradicts a PDF, add a new source row and update the fact. Do not silently overwrite.

| ID | What | Path or citation | Used for |
|---|---|---|---|
| S-README | Package index, v. the data drop | `/Users/chirill/Downloads/assets_for_participants/README.md` (file date 24 Sep 2026) | Folder contract, example counts, licence, start coordinates, tile spec |
| S-DESC | Challenge description, 5 pages, title “Vineyard AI Field Challenge”, producer WeasyPrint 70.0 | `03_docs/Vineyard_AI_Field_Challenge_description.pdf` | Problem, scope, submission, rules, scoring, named datasets |
| S-RULES | Annotation rules v1.0, 25 Sep 2026, 8 pages | `03_docs/Vineyard_AI_annotation_rules.pdf` | Labels, attributes, drawing rules, ZIP appendix |
| S-MARCAJ | Marcaj quick-start v1.0, 25 Sep 2026, 6 pages | `03_docs/Marcaj_quick_start_for_teams.pdf` | Account, upload, publish, editor, submit |
| S-EX | Example CVAT project | `05_examples/siret3_examples_cvat.zip` → `annotations.xml`, two TIFFs | Real XML, object counts, point statistics |
| S-GEO | Measurements made while writing this file, 2026-09-25 | GeoTIFF tags of one or more tiles and of the source BigTIFF; shoelace areas of the GeoJSON; ZIP central directories | Grid formula, GSD check, areas, part byte sizes, image dimensions |
| S-PREVIEW | Qualitative read of the PNG/JPG previews | `01_tiles/overview.png`, `02_route/preview_passages_forbidden.png`, `05_examples/preview_siret3_r021_c012.jpg`, `05_examples/preview_siret3_r006_c004.jpg` | Site layout and example appearance. Not used for measurements. |
| S-RISE | Riseholme COCO vineyard set, opened 2026-09-25 | https://doi.org/10.5281/zenodo.19234906 | Classes, counts, CC BY 4.0, zip size |
| S-AGRIDS | AGRIDS YOLO vineyard set, opened 2026-09-25 | https://doi.org/10.5281/zenodo.15211733 | CC BY-NC-ND 4.0, altitudes |
| S-WASTE | DroneWaste, opened 2026-09-25 | https://doi.org/10.5281/zenodo.17045559 | Landfill boxes, CC BY 4.0 |
| S-UAVV | UAVVaste, opened 2026-09-25 | https://doi.org/10.5281/zenodo.8214061 and Kraft et al., Remote Sensing 2021, 13, 965 | Aerial litter boxes |
| S-UOP | UOPNOA record and Pedrayes et al., Remote Sensing 2021, 13, 2292 | https://doi.org/10.5281/zenodo.4648002 | Plot masks, 0.25 m/px, CC BY 4.0 |
| S-BARROS | Barros et al. vineyard orthomosaics | arXiv:2108.01200 and https://github.com/Cybonic/DL_vineyard_segmentation_study | GSD and semantic vine masks |
| S-ESCA | EscaYard, opened 2026-09-25 | https://doi.org/10.5281/zenodo.10362567 | Trunk points, not canopy polygons |

External names mentioned by the brief and still not fetched: OpenAerialMap, SAM, YOLO.

### How to extend this file

1. New fact from an organizer: add a source row, then update the fact section and the retrieval comment at the top if a keyword changes.
2. New measurement: tag it `MEASURED`, name the file, and date it.
3. New team decision: only [Solution workspace](#solution-workspace) and the decision log.
4. New experiment: only [Research paths](#research-paths) and the findings log.
5. Do not copy the orthomosaic or the tile ZIPs into git. They are large, and the imagery licence requires attribution wherever they are redistributed.

---

## Glossary

| Term | Meaning |
|---|---|
| Block | Connected grapevine planting. One `vineyard_id`. Split by any road or track, or by ≥ 5 m of non-vineyard ground. |
| Canopy | Foliage of one vine, label `vineyard`. |
| Inter-row | Walkable ground between two neighbouring rows’ canopies. Not the strip from axis to axis. |
| Passage | Organizer polygon where walking is allowed (buffered OSM roads/tracks, plus five hand-digitised passages). |
| Forbidden | Organizer polygon the route must not enter (village core, buildings buffered 1 m, some compounds). |
| Inspection location | A gap or missing planting the route should visit. Produced by the team, not drawn in Marcaj. |
| Tile | One supplied 2048×2048 GeoTIFF. |
| Job | Marcaj work unit of up to 5 tiles. Only a submitted job is scored. |
| Study area | Union of the 311 tiles, 81.527 ha. |
| Sireț3 / Siret3 | The orthomosaic and the tile-name prefix. |
