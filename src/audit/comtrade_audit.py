import sys
import time
from datetime import datetime
from pathlib import Path
import pandas as pd
import requests

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import COMTRADE_AUDIT_DIR, COMTRADE_CODES, COUNTRIES, STUDY_END, STUDY_START

BASE_URL = "https://comtradeapi.un.org/public/v1/preview"


def check_comtrade_year(country_name: str, reporter_code: int, year: int):
    url = f"{BASE_URL}/C/A/HS"
    params = {
        "reporterCode": reporter_code,
        "period": year,
        "flowCode": "X",
        "partnerCode": 0,
        "maxRecords": 5,
    }
    try:
        response = requests.get(url, params=params, timeout=30)
        if response.status_code != 200:
            return {
                "Country": country_name, "ReporterCode": reporter_code, "Year": year,
                "HTTP": response.status_code, "Records": 0, "Status": "HTTP ERROR"
            }
        data = response.json()
        records = data.get("data", [])
        status = "AVAILABLE" if records else "NO DATA RETURNED"
        return {
            "Country": country_name, "ReporterCode": reporter_code, "Year": year,
            "HTTP": response.status_code, "Records": len(records), "Status": status
        }
    except Exception as exc:
        return {
            "Country": country_name, "ReporterCode": reporter_code, "Year": year,
            "HTTP": None, "Records": 0, "Status": f"ERROR: {str(exc)}"
        }


def run_comtrade_audit():
    COMTRADE_AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    print(f"Running UN Comtrade availability audit ({STUDY_START}-{STUDY_END})...")
    for code, country in COUNTRIES.items():
        reporter_code = COMTRADE_CODES[code]
        print(f"Auditing {country} (M49: {reporter_code})...")
        for year in range(STUDY_START, STUDY_END + 1):
            res = check_comtrade_year(country, reporter_code, year)
            results.append(res)
            time.sleep(0.25)

    df = pd.DataFrame(results)
    raw_csv = COMTRADE_AUDIT_DIR / "COMTRADE_REPORTER_YEAR_AVAILABILITY.csv"
    df.to_csv(raw_csv, index=False)

    summary_rows = []
    total_expected = STUDY_END - STUDY_START + 1
    for country in COUNTRIES.values():
        sub = df[(df["Country"] == country) & (df["Status"] == "AVAILABLE")]
        years = sorted(sub["Year"].tolist())
        if years:
            missing = sorted(set(range(STUDY_START, STUDY_END + 1)) - set(years))
            summary_rows.append({
                "Country": country,
                "FirstYear": min(years),
                "LastYear": max(years),
                "YearsAvailable": len(years),
                "CoveragePercent": round(len(years) / total_expected * 100, 1),
                "MissingYears": ", ".join(map(str, missing)) if missing else "None",
            })
        else:
            summary_rows.append({
                "Country": country,
                "FirstYear": None,
                "LastYear": None,
                "YearsAvailable": 0,
                "CoveragePercent": 0.0,
                "MissingYears": f"{STUDY_START}-{STUDY_END}",
            })

    summary_df = pd.DataFrame(summary_rows)
    summary_csv = COMTRADE_AUDIT_DIR / "COMTRADE_COVERAGE_SUMMARY.csv"
    summary_df.to_csv(summary_csv, index=False)

    print("\nComtrade coverage summary:")
    print(summary_df.to_string(index=False))
    print(f"\nSaved outputs to: {COMTRADE_AUDIT_DIR}")


if __name__ == "__main__":
    run_comtrade_audit()
