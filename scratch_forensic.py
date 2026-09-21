import pandas as pd
import numpy as np
from pathlib import Path

root = Path(r"C:\Users\tngur\Desktop\modules\sem2\rp\Innovation_Ecosystem")
data_dir = root / "data"

print("==================================================")
print("PART 2 & 10: ALL VARIABLES IN WDI RAW")
print("==================================================")
wdi_long = pd.read_csv(data_dir / "raw/wdi/wdi_raw_long.csv")
wdi_summary = wdi_long.groupby(["variable", "indicator"]).agg(
    total_obs=("value", "count"),
    min_year=("year", "min"),
    max_year=("year", "max"),
    countries=("country_code", lambda x: list(x.unique()))
).reset_index()
print(wdi_summary.to_string())

print("\n==================================================")
print("MISSINGNESS PER VARIABLE PER COUNTRY IN WDI RAW (2000-2025, N=26)")
print("==================================================")
wdi_wide = pd.read_csv(data_dir / "raw/wdi/wdi_raw_wide.csv")
for var in wdi_summary["variable"]:
    p = wdi_wide.pivot(index="year", columns="country_code", values=var)
    counts = p.notna().sum()
    print(f"\nVariable: {var}")
    for c, cnt in counts.items():
        min_y = p[c].dropna().index.min() if cnt > 0 else "None"
        max_y = p[c].dropna().index.max() if cnt > 0 else "None"
        print(f"  {c}: {cnt}/26 obs ({min_y}-{max_y})")

print("\n==================================================")
print("PART 4: COMPLETE CASES IN ORIGINAL 6 COUNTRIES")
print("==================================================")
# Check across 2000-2025 and 2007-2024
master_oecd = pd.read_csv(data_dir / "processed/master/master_after_oecd.csv")
core_vars = ['fdi', 'fixed_broadband', 'hightech_exports', 'internet_users', 
             'manufacturing_value_added', 'patent_nonresident', 'patent_resident', 
             'rd_expenditure', 'researchers_rd', 'tertiary_enrolment', 'government_education']

print("Across all 11 variables in master_after_oecd (N=156):")
complete_all = master_oecd.dropna(subset=core_vars)
print(f"Complete cases count: {len(complete_all)} / 156")
print(complete_all[["country_code", "year"]])

# Drop researchers_rd and government_education (the high missingness ones)
reduced_vars = ['fdi', 'fixed_broadband', 'hightech_exports', 'internet_users', 
                'manufacturing_value_added', 'patent_nonresident', 'patent_resident', 
                'rd_expenditure', 'tertiary_enrolment']
complete_reduced = master_oecd.dropna(subset=reduced_vars)
print(f"\nComplete cases count (without researchers_rd & gov_ed): {len(complete_reduced)} / 156")
print(complete_reduced.groupby("country_code")["year"].agg(["count", "min", "max"]))

# Complete cases in 2007-2024
m_2007 = master_oecd[(master_oecd["year"] >= 2007) & (master_oecd["year"] <= 2024)]
print(f"\nIn window 2007-2024 (theoretical 6*18 = 108):")
complete_2007_reduced = m_2007.dropna(subset=reduced_vars)
print(f"Complete cases count (reduced vars, 2007-2024): {len(complete_2007_reduced)} / 108")
print(complete_2007_reduced.groupby("country_code")["year"].agg(["count", "min", "max"]))

print("\n==================================================")
print("PART 11: PATENTS IN WDI, WIPO, TAIWAN")
print("==================================================")
print("WDI Patent Resident vs Non-Resident stats:")
print(wdi_wide.groupby("country_code")[["patent_resident", "patent_nonresident"]].agg(["count", "min", "max"]))

wipo_clean = data_dir / "raw/wipo/wipo_patents_clean_2000_2024.csv"
if wipo_clean.exists():
    df_wipo = pd.read_csv(wipo_clean)
    print("\nWIPO Clean shape:", df_wipo.shape)
    print("Columns:", list(df_wipo.columns))
    print(df_wipo.head(10))

taiwan_pat = data_dir / "raw/taiwan/taiwan_patent_complete_2000_2025.csv"
if taiwan_pat.exists():
    df_tw = pd.read_csv(taiwan_pat)
    print("\nTaiwan Patent shape:", df_tw.shape)
    print("Columns:", list(df_tw.columns))
    print(df_tw.head(10))

print("\n==================================================")
print("PART 13: SEQUENTIAL MASTER DATASETS COMPARISON")
print("==================================================")
# Let's compare master_after_oecd, master_after_patents, master_after_tertiary, master_after_broadband, master_after_internet, master_after_hightech
m_files = ["master_after_oecd.csv", "master_after_patents.csv", "master_after_tertiary.csv", 
           "master_after_broadband.csv", "master_after_internet.csv", "master_after_hightech.csv"]

for mf in m_files:
    p = data_dir / "processed/master" / mf
    if p.exists():
        df = pd.read_csv(p)
        print(f"{mf}: shape={df.shape}, cols={len(df.columns)}")
        # Check if IP.PAT.RESD is different from patent_resident
        if "IP.PAT.RESD" in df.columns:
            diff_res = (df["IP.PAT.RESD"] != df["patent_resident"]).sum()
            print(f"   IP.PAT.RESD vs patent_resident differences: {diff_res}")
