"""
Generate Marcaj CVAT for Images 1.1 annotations.xml from tile imagery.
Performs model inference to extract canopy coordinates, derives row centerlines
and inter-row polygons, and produces the final XML. Zero image files generated.
"""

import argparse
import json
from pathlib import Path
from typing import List

from src.pipeline import VineyardPipeline
from src.export.cvat_writer import CVATWriter


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run inference on tiles and generate Marcaj CVAT 1.1 XML."
    )
    parser.add_argument(
        "--source",
        type=str,
        default="assets/05_examples/siret3_examples_cvat/images",
        help="Path to a single .tif/.jpg file or a directory containing tiles",
    )
    parser.add_argument(
        "--weights",
        type=str,
        default="weights/best.pt",
        help="Path to trained model weights (default: weights/best.pt)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="annotations.xml",
        help="Output XML file path (default: annotations.xml)",
    )
    parser.add_argument(
        "--conf",
        type=float,
        default=0.28,
        help="Confidence threshold for canopy detection (default: 0.28)",
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=1024,
        help="Image size for inference (default: 1024)",
    )
    parser.add_argument(
        "--vineyard-id",
        type=str,
        default="V01",
        help="Block ID prefix (default: V01)",
    )
    parser.add_argument(
        "--save-json",
        type=str,
        default="",
        help="Optional path to dump raw extracted coordinates as JSON",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    source_path = Path(args.source)
    if not source_path.exists():
        raise FileNotFoundError(f"Source path not found: {source_path}")

    # Gather image files
    if source_path.is_file():
        tile_files = [source_path]
    else:
        tile_files = sorted(
            [f for f in source_path.iterdir() if f.suffix.lower() in [".tif", ".tiff", ".jpg", ".jpeg", ".png"]]
        )

    if not tile_files:
        print(f"No image files found in {source_path}")
        return

    print("=" * 60)
    print("Marcaj CVAT 1.1 XML Generator")
    print(f"Model Weights: {args.weights}")
    print(f"Source:        {args.source} ({len(tile_files)} tiles)")
    print(f"Confidence:    {args.conf} | ImgSz: {args.imgsz}")
    print(f"Output XML:    {args.output}")
    print("=" * 60)

    # Initialize pipeline
    pipeline = VineyardPipeline(model_weights_path=args.weights)
    writer = CVATWriter(task_name="Vineyard AI Field Challenge")

    raw_coordinates_dump = {}

    for idx, tile_file in enumerate(tile_files, start=1):
        tile_ann, targets = pipeline.process_tile(
            tile_path=str(tile_file),
            vineyard_id=args.vineyard_id,
            confidence=args.conf,
            imgsz=args.imgsz,
        )
        writer.add_tile(tile_ann)

        print(
            f"[{idx}/{len(tile_files)}] {tile_file.name}: "
            f"{len(tile_ann.canopies)} canopies, "
            f"{len(tile_ann.rows)} rows, "
            f"{len(tile_ann.interrows)} inter-rows, "
            f"{len(targets)} gap targets"
        )

        if args.save_json:
            raw_coordinates_dump[tile_file.name] = {
                "canopies": [c.points for c in tile_ann.canopies],
                "rows": [
                    {
                        "row_id": r.row_id,
                        "structure": r.row_structure,
                        "points": r.points,
                    }
                    for r in tile_ann.rows
                ],
                "interrows": [
                    {
                        "cover": ir.interrow_cover,
                        "points": ir.points,
                    }
                    for ir in tile_ann.interrows
                ],
                "gaps": targets,
            }

    # Write final CVAT 1.1 XML
    out_xml_path = Path(args.output)
    out_xml_path.parent.mkdir(parents=True, exist_ok=True)
    writer.write(str(out_xml_path))
    print("=" * 60)
    print(f"Successfully generated: {out_xml_path.resolve()}")

    # Optional JSON dump
    if args.save_json:
        out_json_path = Path(args.save_json)
        out_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_json_path, "w", encoding="utf-8") as f:
            json.dump(raw_coordinates_dump, f, indent=2)
        print(f"Raw coordinates dumped to: {out_json_path.resolve()}")


if __name__ == "__main__":
    main()

