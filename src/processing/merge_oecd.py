import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import COUNTRIES, MASTER_DIR, OECD_RAW_DIR, STUDY_END, STUDY_START, WDI_RAW_DIR


def run_oecd_merge():
    MASTER_DIR.mkdir(parents=True, exist_ok=True)
    wdi_path = WDI_RAW_DIR / "wdi_raw_wide.csv"
    oecd_path = OECD_RAW_DIR / "oecd_msti_raw.csv"

    if not wdi_path.exists() or not oecd_path.exists():
        print(f"Required inputs missing: {wdi_path} or {oecd_path}")
        return

    wdi = pd.read_csv(wdi_path)
    oecd = pd.read_csv(oecd_path)

    oecd["TIME_PERIOD"] = pd.to_numeric(oecd["TIME_PERIOD"], errors="coerce")
    oecd["OBS_VALUE"] = pd.to_numeric(oecd["OBS_VALUE"], errors="coerce")
    oecd = oecd[oecd["TIME_PERIOD"].between(STUDY_START, STUDY_END)].copy()

    # GERD / R&D expenditure (% GDP)
    gerd = oecd[(oecd["MEASURE"] == "G") & (oecd["UNIT_MEASURE"] == "PT_B1GQ")].copy()
    gerd = (
        gerd[["REF_AREA", "TIME_PERIOD", "OBS_VALUE", "OBS_STATUS"]]
        .rename(columns={
            "REF_AREA": "country_code",
            "TIME_PERIOD": "year",
            "OBS_VALUE": "oecd_rd_expenditure",
            "OBS_STATUS": "oecd_rd_status"
        })
        .sort_values(["country_code", "year"])
        .drop_duplicates(subset=["country_code", "year"], keep="first")
    )

    # Researchers (FTE)
    researchers = oecd[(oecd["MEASURE"] == "T_RS") & (oecd["UNIT_MEASURE"] == "FTE")].copy()
    researchers["_priority"] = researchers["TRANSFORMATION"].isna().astype(int)
    researchers = (
        researchers.sort_values(["REF_AREA", "TIME_PERIOD", "_priority"], ascending=[True, True, False])
        .drop_duplicates(subset=["REF_AREA", "TIME_PERIOD"], keep="first")
        [["REF_AREA", "TIME_PERIOD", "OBS_VALUE", "OBS_STATUS"]]
        .rename(columns={
            "REF_AREA": "country_code",
            "TIME_PERIOD": "year",
            "OBS_VALUE": "oecd_researchers_rd",
            "OBS_STATUS": "oecd_researchers_status"
        })
    )

    # Complete grid merge
    grid = [
        {"country_code": code, "country": name, "year": y}
        for code, name in COUNTRIES.items()
        for y in range(STUDY_START, STUDY_END + 1)
    ]
    master = pd.DataFrame(grid)
    master = master.merge(wdi, on=["country_code", "country", "year"], how="left")
    master = master.merge(gerd, on=["country_code", "year"], how="left")
    master = master.merge(researchers, on=["country_code", "year"], how="left")

    # Source reconciliation: prioritize WDI, fill with OECD
    if "rd_expenditure" in master.columns:
        master["rd_expenditure_wdi"] = master["rd_expenditure"]
        master["rd_expenditure"] = master["rd_expenditure"].combine_first(master["oecd_rd_expenditure"])
        master["rd_expenditure_source"] = "MISSING"
        master.loc[master["rd_expenditure_wdi"].notna(), "rd_expenditure_source"] = "WDI"
        master.loc[master["rd_expenditure_wdi"].isna() & master["oecd_rd_expenditure"].notna(), "rd_expenditure_source"] = "OECD"

    if "researchers_rd" in master.columns:
        master["researchers_rd_wdi"] = master["researchers_rd"]
        master["researchers_rd"] = master["researchers_rd"].combine_first(master["oecd_researchers_rd"])
        master["researchers_rd_source"] = "MISSING"
        master.loc[master["researchers_rd_wdi"].notna(), "researchers_rd_source"] = "WDI"
        master.loc[master["researchers_rd_wdi"].isna() & master["oecd_researchers_rd"].notna(), "researchers_rd_source"] = "OECD"

    master_file = MASTER_DIR / "master_after_oecd.csv"
    master.to_csv(master_file, index=False)

    # Track remaining gaps
    gap_rows = []
    for code, country in COUNTRIES.items():
        sub = master[master["country_code"] == code]
        for var in ["rd_expenditure", "researchers_rd"]:
            if var in sub.columns:
                for y in sub[sub[var].isna()]["year"]:
                    gap_rows.append({
                        "country_code": code, "country": country, "year": y,
                        "variable": var, "source_needed": "OECD MSTI"
                    })
    gaps_df = pd.DataFrame(gap_rows)
    gaps_df.to_csv(MASTER_DIR / "oecd_remaining_gaps.csv", index=False)

    print(f"Merged master dataset generated with {len(master)} rows.")
    print(f"Saved: {master_file}")
    print(f"Remaining OECD gaps: {len(gaps_df)}")


if __name__ == "__main__":
    run_oecd_merge()
