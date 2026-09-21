import sys
from pathlib import Path
import pandas as pd
import requests

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import OECD_RAW_DIR, STUDY_END, STUDY_START

OECD_SDMX_URL = (
    "https://sdmx.oecd.org/public/rest/data/"
    "OECD.STI.STP,DSD_MSTI@DF_MSTI,1.3/"
    ".A.G+T_RS...?"
    f"startPeriod={STUDY_START}&"
    f"endPeriod={STUDY_END}&"
    "dimensionAtObservation=AllDimensions&"
    "format=csvfile"
)


def download_oecd_msti():
    OECD_RAW_DIR.mkdir(parents=True, exist_ok=True)
    print("Requesting OECD MSTI dataset via SDMX API...")
    headers = {"Accept": "text/csv"}

    try:
        response = requests.get(OECD_SDMX_URL, headers=headers, timeout=120)
        if response.status_code != 200:
            print(f"OECD download failed with status {response.status_code}")
            return False

        raw_csv_path = OECD_RAW_DIR / "oecd_msti_raw.csv"
        raw_csv_path.write_bytes(response.content)
        print(f"Saved raw OECD dataset: {raw_csv_path}")

        df = pd.read_csv(raw_csv_path)
        cols_path = OECD_RAW_DIR / "oecd_columns.txt"
        cols_path.write_text("\n".join(map(str, df.columns)) + "\n", encoding="utf-8")

        sample_path = OECD_RAW_DIR / "oecd_msti_sample.csv"
        df.head(1000).to_csv(sample_path, index=False)

        print(f"OECD extraction complete. Total rows: {len(df):,}")
        return True

    except Exception as exc:
        print(f"OECD extraction error: {exc}")
        return False


if __name__ == "__main__":
    download_oecd_msti()
