import logging
import argparse
import json
import csv
import warnings
from pathlib import Path
from textwrap import dedent
from statistics import median_low

from pydicom import Dataset, dcmread
from pydicom.errors import InvalidDicomError

from Classificazione import classificazione


def select_central_slice_in_series(series_dir: Path) -> Path:
    """Return path of DICOM image file corresponding to the central
    slice, i.e. image having the median InstanceNumber value."""
    
    # Read in the InstanceNumber of all images in series directory
    instance_numbers = {}
    img_paths = (i for i in series_dir.iterdir() if i.is_file())
    for img_path in img_paths:
        try:
            with dcmread(img_path, stop_before_pixels=True, specific_tags=["InstanceNumber"]) as img_ds:
                instance_numbers[img_ds.InstanceNumber] = img_path
        except InvalidDicomError as ex:
            # Ignore non-DICOM files
            logging.error(ex)
            continue

    median_instance_num = median_low(instance_numbers.keys())
    return instance_numbers[median_instance_num]


def predict_series(series_dir: Path) -> dict:
    """Classify series based on central slice image"""

    central_slice_image_path = select_central_slice_in_series(series_dir)
    prediction = classificazione([str(central_slice_image_path)])

    with dcmread(central_slice_image_path, stop_before_pixels=True, specific_tags=["SeriesInstanceUID"]) as img_ds:
        series_instance_uid = img_ds.SeriesInstanceUID

    return {
        "series_instance_uid": series_instance_uid,
        "dir_path": str(series_dir),
        "prediction": prediction
    }


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=dedent(
            """
            Classify MRI series as brain or non-brain. 
            Takes a directory of DICOM files as input 
            and optionally write results to a CSV file.
            """
        ),
    )
    path_args_group = parser.add_mutually_exclusive_group(required=True)
    path_args_group.add_argument(
        "--series-paths-file",
        type=argparse.FileType("r", encoding="utf-8"),
        help="TXT file listing DICOM series directory paths (one path per line)",
    )
    path_args_group.add_argument(
        "--series-dirs",
        nargs="+",
        help="One or more DICOM series directory paths containing DICOM image files",
    )
    parser.add_argument(
        "--csv-file",
        type=argparse.FileType("w", encoding="utf-8"),
        help="Optional CSV file where results will be written (by default, writes to stdout)",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Disable log output"
    )

    args = parser.parse_args()

    if args.quiet:
        logging.getLogger().disabled = True
        warnings.filterwarnings('ignore')

    columns = ["series_instance_uid", "dir_path", "prediction"]
    if args.csv_file:
        writer = csv.DictWriter(args.csv_file, fieldnames=columns)
        writer.writeheader()

    if args.series_paths_file:
        all_series = (line.rstrip("\n") for line in args.series_paths_file.readlines())
    elif args.series_dirs:
        all_series = args.series_dirs
    else:
        raise ValueError("Must specify either '--series-paths-file' or '--series-dirs'")
        

    results_all = {}
    for series_dir in all_series:
        logging.debug("Predicting series '%s'", series_dir)
        results = {}

        try:
            results = predict_series(Path(series_dir))
            if "dir_path" in results:
                results_all[results["dir_path"]] = {"prediction": results["prediction"]}

            if args.csv_file:
                writer.writerow(results)

        except Exception as ex:
            logging.error("Error predicting series '%s'", series_dir)
            logging.exception(ex)

    print(json.dumps(results_all))


if __name__ == "__main__":
    main()

