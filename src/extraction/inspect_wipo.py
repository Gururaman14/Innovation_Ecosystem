import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import WIPO_RAW_DIR


def inspect_workbooks():
    patents_dir = WIPO_RAW_DIR / "patents_2025"
    if not patents_dir.exists():
        print(f"Directory not found: {patents_dir}")
        return

    workbooks = sorted(patents_dir.glob("*.xlsx"))
    print(f"Inspecting {len(workbooks)} WIPO workbook(s) in {patents_dir}...\n")

    for file in workbooks:
        print(f"--- Workbook: {file.name} ---")
        try:
            xls = pd.ExcelFile(file)
            for sheet in xls.sheet_names:
                df = pd.read_excel(file, sheet_name=sheet, header=None)
                print(f"Sheet '{sheet}': shape {df.shape}")
                preview = df.head(5).dropna(how="all")
                if not preview.empty:
                    print(preview.to_string(index=False, header=False))
                print()
        except Exception as exc:
            print(f"Error reading {file.name}: {exc}\n")


if __name__ == "__main__":
    inspect_workbooks()
