import sys
import time
from pathlib import Path
import pandas as pd
import requests

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import COUNTRIES, COVERAGE_DIR, INDICATORS, STUDY_END, STUDY_START, STUDY_YEARS

EXPECTED_OBS = len(STUDY_YEARS)


def get_wdi(country_code: str, indicator: str):
    url = f"https://api.worldbank.org/v2/country/{country_code}/indicator/{indicator}?format=json&per_page=100"
    try:
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            return {}, f"HTTP {response.status_code}"
        payload = response.json()
        if not isinstance(payload, list) or len(payload) < 2:
            return {}, "Invalid API response"

        data = {}
        for row in payload[1]:
            if row.get("date") is None:
                continue
            year = int(row["date"])
            if STUDY_START <= year <= STUDY_END and row.get("value") is not None:
                data[year] = row["value"]
        return data, None
    except Exception as exc:
        return {}, str(exc)


def run_audit():
    COVERAGE_DIR.mkdir(parents=True, exist_ok=True)
    detail_rows = []
    matrix_rows = []

    for country_code, country_name in COUNTRIES.items():
        print(f"Auditing {country_name} ({country_code})...")
        country_matrix = {"country_code": country_code, "country": country_name}

        for var_name, ind_code in INDICATORS.items():
            data, error = get_wdi(country_code, ind_code)
            available = sorted(data.keys())
            missing = [y for y in STUDY_YEARS if y not in available]
            count = len(available)
            coverage_pct = round((count / EXPECTED_OBS) * 100, 1)

            if error:
                status = "API_ERROR"
            elif count == EXPECTED_OBS:
                status = "COMPLETE"
            elif count == 0:
                status = "NO_DATA"
            else:
                status = "PARTIAL"

            detail_rows.append({
                "country_code": country_code,
                "country": country_name,
                "variable": var_name,
                "indicator": ind_code,
                "expected_years": EXPECTED_OBS,
                "available_count": count,
                "missing_count": len(missing),
                "coverage_percent": coverage_pct,
                "first_year": min(available) if available else None,
                "last_year": max(available) if available else None,
                "available_years": ",".join(map(str, available)),
                "missing_years": ",".join(map(str, missing)),
                "status": status,
                "error": error,
            })
            country_matrix[var_name] = coverage_pct
            time.sleep(0.2)

        matrix_rows.append(country_matrix)

    detail_df = pd.DataFrame(detail_rows)
    detail_df.to_csv(COVERAGE_DIR / "coverage_detail.csv", index=False)

    summary_rows = []
    for country_code, country_name in COUNTRIES.items():
        sub = detail_df[detail_df["country_code"] == country_code]
        summary_rows.append({
            "country_code": country_code,
            "country": country_name,
            "indicators": len(sub),
            "complete_indicators": (sub["status"] == "COMPLETE").sum(),
            "partial_indicators": (sub["status"] == "PARTIAL").sum(),
            "no_data_indicators": (sub["status"] == "NO_DATA").sum(),
            "api_error_indicators": (sub["status"] == "API_ERROR").sum(),
            "average_coverage_percent": round(sub["coverage_percent"].mean(), 1),
        })
    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(COVERAGE_DIR / "coverage_summary.csv", index=False)

    matrix_df = pd.DataFrame(matrix_rows)
    matrix_df.to_csv(COVERAGE_DIR / "master_coverage_matrix.csv", index=False)

    common_rows = []
    for country_code, country_name in COUNTRIES.items():
        sub = detail_df[detail_df["country_code"] == country_code]
        sets = [
            {int(y) for y in row["available_years"].split(",")}
            for _, row in sub.iterrows() if row["available_years"]
        ]
        common = sorted(set.intersection(*sets)) if sets else []
        common_rows.append({
            "country_code": country_code,
            "country": country_name,
            "common_year_count": len(common),
            "common_coverage_percent": round(len(common) / EXPECTED_OBS * 100, 1),
            "common_years": ",".join(map(str, common)),
            "first_common_year": min(common) if common else None,
            "last_common_year": max(common) if common else None,
        })
    common_df = pd.DataFrame(common_rows)
    common_df.to_csv(COVERAGE_DIR / "common_years.csv", index=False)

    print("\nCoverage audit complete. Output files saved to:", COVERAGE_DIR)


if __name__ == "__main__":
    run_audit()
