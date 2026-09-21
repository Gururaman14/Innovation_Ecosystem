import sys
import time
from pathlib import Path
import pandas as pd
import requests

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import AUDIT_18_DIR, STUDY_END, STUDY_START, STUDY_YEARS

BASE_URL = "https://api.worldbank.org/v2"

COUNTRY_GROUPS = {
    "India": {"iso3": "IND", "alternatives": [("Vietnam", "VNM"), ("Malaysia", "MYS")]},
    "China": {"iso3": "CHN", "alternatives": [("Japan", "JPN"), ("Singapore", "SGP")]},
    "South Korea": {"iso3": "KOR", "alternatives": [("Japan", "JPN"), ("Singapore", "SGP")]},
    "Taiwan": {"iso3": "TWN", "alternatives": [("Singapore", "SGP"), ("Malaysia", "MYS")]},
    "Israel": {"iso3": "ISR", "alternatives": [("Netherlands", "NLD"), ("Sweden", "SWE")]},
    "Brazil": {"iso3": "BRA", "alternatives": [("Mexico", "MEX"), ("Türkiye", "TUR")]},
}

INDICATORS = {
    "HighTech_Exports": "TX.VAL.TECH.MF.ZS",
    "RD_Expenditure": "GB.XPD.RSDV.GD.ZS",
    "Researchers_RD": "SP.POP.SCIE.RD.P6",
    "Patent_Resident": "IP.PAT.RESD",
    "Patent_NonResident": "IP.PAT.NRES",
    "Internet_Users": "IT.NET.USER.ZS",
    "Fixed_Broadband": "IT.NET.BBND.P2",
    "Tertiary_Enrolment": "SE.TER.ENRR",
    "Gov_Education_Expenditure": "SE.XPD.TOTL.GD.ZS",
    "FDI": "BX.KLT.DINV.WD.GD.ZS",
    "Manufacturing_Value_Added": "NV.IND.MANF.ZS",
}


def get_indicator(country_code: str, indicator_code: str):
    url = f"{BASE_URL}/country/{country_code}/indicator/{indicator_code}"
    params = {"format": "json", "date": f"{STUDY_START}:{STUDY_END}", "per_page": 100}
    try:
        resp = requests.get(url, params=params, timeout=60)
        if resp.status_code != 200:
            return {}
        data = resp.json()
        if len(data) < 2 or not data[1]:
            return {}
        obs = {}
        for row in data[1]:
            year = int(row["date"])
            val = row.get("value")
            if val is not None:
                obs[year] = val
        return obs
    except Exception:
        return {}


def run_country_selection_audit():
    AUDIT_18_DIR.mkdir(parents=True, exist_ok=True)
    country_list = []
    for orig, info in COUNTRY_GROUPS.items():
        country_list.append({"Country": orig, "ISO3": info["iso3"], "Group": orig, "Status": "Original"})
        for i, (alt_name, alt_iso) in enumerate(info["alternatives"], 1):
            country_list.append({"Country": alt_name, "ISO3": alt_iso, "Group": orig, "Status": f"Alternative {i}"})

    country_df = pd.DataFrame(country_list).drop_duplicates(subset=["ISO3"]).reset_index(drop=True)
    print(f"Auditing {len(country_df)} countries ({STUDY_START}-{STUDY_END})...")

    audit_records = []
    total_expected = len(STUDY_YEARS)

    for _, c_row in country_df.iterrows():
        iso = c_row["ISO3"]
        name = c_row["Country"]
        print(f"Checking {name} ({iso})...")

        for var_name, ind_code in INDICATORS.items():
            obs = get_indicator(iso, ind_code)
            years = sorted(obs.keys())
            count = len(years)
            pct = round(count / total_expected * 100, 1)
            audit_records.append({
                "Group": c_row["Group"],
                "Status": c_row["Status"],
                "Country": name,
                "ISO3": iso,
                "Variable": var_name,
                "Indicator": ind_code,
                "Years_Available": count,
                "Expected_Years": total_expected,
                "Coverage_Percent": pct,
                "First_Year": min(years) if years else None,
                "Last_Year": max(years) if years else None,
            })
            time.sleep(0.15)

    audit_df = pd.DataFrame(audit_records)
    audit_df.to_csv(AUDIT_18_DIR / "18_country_full_coverage_audit.csv", index=False)

    summary_df = (
        audit_df.groupby(["Group", "Status", "Country", "ISO3"])
        .agg(
            Average_Coverage=("Coverage_Percent", "mean"),
            Min_Coverage=("Coverage_Percent", "min"),
            Complete_Variables=("Coverage_Percent", lambda s: (s == 100).sum()),
            Zero_Variables=("Coverage_Percent", lambda s: (s == 0).sum()),
        )
        .reset_index()
    )
    summary_df["Average_Coverage"] = summary_df["Average_Coverage"].round(1)
    summary_df.to_csv(AUDIT_18_DIR / "18_country_summary.csv", index=False)

    comparison_df = summary_df.sort_values(by=["Group", "Average_Coverage"], ascending=[True, False])
    comparison_df.to_csv(AUDIT_18_DIR / "country_group_comparison.csv", index=False)

    print("\nGroup comparison summary:")
    print(comparison_df.to_string(index=False))
    print(f"\nOutputs saved to: {AUDIT_18_DIR}")


if __name__ == "__main__":
    run_country_selection_audit()
