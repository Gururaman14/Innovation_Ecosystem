import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import COUNTRIES, GAP_ANALYSIS_DIR, INDICATORS, STUDY_END, STUDY_START, WDI_RAW_DIR

SOURCE_MAP = {
    "hightech_exports": "UN Comtrade / WITS",
    "rd_expenditure": "OECD MSTI",
    "researchers_rd": "OECD MSTI",
    "patent_resident": "WIPO",
    "patent_nonresident": "WIPO",
    "internet_users": "ITU",
    "fixed_broadband": "ITU",
    "tertiary_enrolment": "UNESCO UIS",
    "government_education": "UNESCO UIS",
    "fdi": "WDI / UNCTAD",
    "manufacturing_value_added": "WDI / UNIDO",
}


def run_gap_analysis():
    GAP_ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    raw_file = WDI_RAW_DIR / "wdi_raw_wide.csv"

    if not raw_file.exists():
        print(f"Error: {raw_file} not found. Run extraction first.")
        return

    df = pd.read_csv(raw_file)

    grid = [
        {"country_code": code, "country": country, "year": year}
        for code, country in COUNTRIES.items()
        for year in range(STUDY_START, STUDY_END + 1)
    ]
    grid_df = pd.DataFrame(grid)
    merged = grid_df.merge(df, on=["country_code", "country", "year"], how="left")

    gap_rows = []
    for _, row in merged.iterrows():
        for var in INDICATORS.keys():
            if pd.isna(row.get(var)):
                gap_rows.append({
                    "country_code": row["country_code"],
                    "country": row["country"],
                    "year": row["year"],
                    "variable": var,
                    "recommended_source": SOURCE_MAP.get(var, "Alternative Source"),
                })

    gaps = pd.DataFrame(gap_rows)
    gaps.to_csv(GAP_ANALYSIS_DIR / "all_missing_cells.csv", index=False)

    country_summary = gaps.groupby(["country_code", "country"]).size().reset_index(name="missing_cells")
    country_summary.to_csv(GAP_ANALYSIS_DIR / "missing_by_country.csv", index=False)

    var_summary = (
        gaps.groupby(["variable", "recommended_source"])
        .size()
        .reset_index(name="missing_cells")
        .sort_values("missing_cells", ascending=False)
    )
    var_summary.to_csv(GAP_ANALYSIS_DIR / "missing_by_variable.csv", index=False)

    c_var = (
        gaps.groupby(["country_code", "country", "variable", "recommended_source"])
        .size()
        .reset_index(name="missing_years")
    )
    c_var.to_csv(GAP_ANALYSIS_DIR / "missing_country_variable.csv", index=False)

    print(f"Gap analysis completed. Total missing cells identified: {len(gaps)}")
    print(f"Outputs saved to: {GAP_ANALYSIS_DIR}")


if __name__ == "__main__":
    run_gap_analysis()
