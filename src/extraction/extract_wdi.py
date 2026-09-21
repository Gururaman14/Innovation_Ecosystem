import sys
import time
from pathlib import Path
import pandas as pd
import requests

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import COUNTRIES, INDICATORS, STUDY_END, STUDY_START, STUDY_YEARS, WDI_RAW_DIR


def fetch_wdi_series(country_code: str, indicator_code: str, max_retries: int = 4):
    url = f"https://api.worldbank.org/v2/country/{country_code}/indicator/{indicator_code}"
    params = {"format": "json", "per_page": 100, "date": f"{STUDY_START}:{STUDY_END}"}
    last_err = None

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=45)
            if resp.status_code != 200:
                last_err = f"HTTP {resp.status_code}"
                time.sleep(1.5)
                continue
            data = resp.json()
            if not isinstance(data, list) or len(data) < 2:
                last_err = "Empty/malformed API response"
                time.sleep(1.5)
                continue

            results = {}
            for item in data[1]:
                if item.get("value") is not None and item.get("date"):
                    year = int(item["date"])
                    if STUDY_START <= year <= STUDY_END:
                        results[year] = item["value"]
            return results, None
        except Exception as exc:
            last_err = str(exc)
            time.sleep(2.0)

    return {}, last_err


def run_extraction():
    WDI_RAW_DIR.mkdir(parents=True, exist_ok=True)
    all_observations = []
    failed_series = []

    print(f"Extracting WDI raw series ({STUDY_START}-{STUDY_END})...")
    for country_code, country_name in COUNTRIES.items():
        print(f"Fetching data for {country_name} ({country_code})...")
        for var_name, ind_code in INDICATORS.items():
            data, err = fetch_wdi_series(country_code, ind_code)
            if err:
                failed_series.append({
                    "country_code": country_code, "country": country_name,
                    "variable": var_name, "indicator": ind_code, "error": err
                })
                print(f"  [ERROR] {var_name}: {err}")
            else:
                for year, val in data.items():
                    all_observations.append({
                        "country_code": country_code, "country": country_name,
                        "year": year, "variable": var_name, "value": val
                    })
            time.sleep(0.15)

    long_df = pd.DataFrame(all_observations)
    long_df.to_csv(WDI_RAW_DIR / "wdi_raw_long.csv", index=False)

    if not long_df.empty:
        wide_df = long_df.pivot_table(
            index=["country_code", "country", "year"],
            columns="variable",
            values="value"
        ).reset_index()
        wide_df.to_csv(WDI_RAW_DIR / "wdi_raw_wide.csv", index=False)

    coverage_summary = []
    for country_code, country_name in COUNTRIES.items():
        sub = long_df[long_df["country_code"] == country_code] if not long_df.empty else pd.DataFrame()
        for var_name, ind_code in INDICATORS.items():
            var_sub = sub[sub["variable"] == var_name] if not sub.empty else pd.DataFrame()
            years = sorted(var_sub["year"].unique()) if not var_sub.empty else []
            coverage_summary.append({
                "country_code": country_code,
                "country": country_name,
                "variable": var_name,
                "indicator": ind_code,
                "observations": len(years),
                "coverage_pct": round(len(years) / len(STUDY_YEARS) * 100, 1),
                "years": ",".join(map(str, years))
            })

    pd.DataFrame(coverage_summary).to_csv(WDI_RAW_DIR / "wdi_coverage_after_retry.csv", index=False)
    pd.DataFrame(failed_series).to_csv(WDI_RAW_DIR / "wdi_errors.csv", index=False)

    print(f"\nExtraction complete. Files written to: {WDI_RAW_DIR}")


if __name__ == "__main__":
    run_extraction()
