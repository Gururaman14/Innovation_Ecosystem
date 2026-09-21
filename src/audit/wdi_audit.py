import sys
import time
from datetime import datetime
from pathlib import Path
import requests
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import COUNTRIES, INDICATOR_LABELS, SOURCES_AUDIT_DIR, STUDY_START, STUDY_END

BASE_URL = "https://api.worldbank.org/v2"
COUNTRY_CODES = ";".join(COUNTRIES.keys())


def fetch_indicator(countries_str: str, indicator: str, start: int = STUDY_START, end: int = STUDY_END):
    url = f"{BASE_URL}/country/{countries_str}/indicator/{indicator}?format=json&per_page=2000&date={start}:{end}"
    try:
        response = requests.get(url, timeout=30, headers={"User-Agent": "academic-audit/1.0"})
        if response.status_code != 200:
            return None, f"HTTP {response.status_code}"
        data = response.json()
        if not isinstance(data, list) or len(data) < 2 or data[1] is None:
            return None, "empty response"
        return data[1], None
    except Exception as exc:
        return None, str(exc)


def calculate_coverage(rows: list, country_code: str):
    matched = [
        r for r in rows
        if r.get("countryiso3code", "") == country_code or r.get("country", {}).get("id", "") == country_code
    ]
    study_years = list(range(STUDY_START, STUDY_END + 1))
    if not matched:
        return {
            "count": len(study_years), "non_null": 0, "start": None, "end": None,
            "missing_pct": 100.0, "missing_years": study_years
        }

    year_map = {int(r["date"]): r["value"] for r in matched if str(r.get("date", "")).isdigit()}
    missing = [y for y in study_years if year_map.get(y) is None]
    non_null = [y for y in study_years if year_map.get(y) is not None]

    return {
        "count": len(study_years),
        "non_null": len(non_null),
        "start": min(non_null) if non_null else None,
        "end": max(non_null) if non_null else None,
        "missing_pct": 100.0 * len(missing) / len(study_years),
        "missing_years": missing,
    }


def run():
    lines = []

    def log(msg=""):
        print(msg)
        lines.append(msg)

    log("DATA AVAILABILITY AUDIT")
    log(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    log(f"Study window: {STUDY_START}-{STUDY_END}\n")

    log("SECTION 1: COUNTRY ACCESSIBILITY")
    country_rows, err = fetch_indicator(COUNTRY_CODES, "TX.VAL.TECH.MF.ZS")
    returned_codes = {r.get("countryiso3code", "") for r in (country_rows or [])}
    log(f"Available codes: {sorted(list(returned_codes))}")
    for code, name in COUNTRIES.items():
        status = "OK" if code in returned_codes else "NO DATA"
        log(f"  [{status:7s}] {code} - {name}")

    log("\nSECTION 2: DEPENDENT VARIABLE COVERAGE (TX.VAL.TECH.MF.ZS)")
    dv_records = []
    last_available = {}
    for code, name in COUNTRIES.items():
        cov = calculate_coverage(country_rows or [], code)
        last_available[code] = cov["end"]
        missing_str = str(cov["missing_years"][:5]) + ("..." if len(cov["missing_years"]) > 5 else "") if cov["missing_years"] else "none"
        dv_records.append({
            "Code": code,
            "Country": name,
            "Non-null": cov["non_null"],
            "Coverage": f"{cov['start']}-{cov['end']}" if cov["start"] else "N/A",
            "Missing %": f"{cov['missing_pct']:.0f}%",
            "Missing Years": missing_str
        })

    dv_df = pd.DataFrame(dv_records)
    try:
        from tabulate import tabulate
        log(tabulate(dv_df, headers="keys", tablefmt="simple", showindex=False))
    except ImportError:
        log(dv_df.to_string(index=False))

    valid_ends = [v for v in last_available.values() if v is not None]
    min_end = min(valid_ends) if valid_ends else None
    log(f"\nUsable study end year: {min_end}")
    log(f"Recommended study window: {STUDY_START}-{min_end}\n")

    log("SECTION 3: PREDICTOR INDICATOR COVERAGE")
    for indicator_code, label in INDICATOR_LABELS.items():
        time.sleep(0.3)
        rows, err = fetch_indicator(COUNTRY_CODES, indicator_code)
        log(f"\n{indicator_code}: {label}")
        for code, name in COUNTRIES.items():
            if err or rows is None:
                log(f"  {code} ({name}): ERROR - {err}")
                continue
            cov = calculate_coverage(rows, code)
            if cov["non_null"] == 0:
                log(f"  {code} ({name}): NO DATA")
            else:
                flag = " [High Missingness >30%]" if cov["missing_pct"] > 30 else ""
                log(f"  {code} ({name}): {cov['non_null']} obs [{cov['start']}-{cov['end']}], missing {cov['missing_pct']:.0f}%{flag}")

    SOURCES_AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = SOURCES_AUDIT_DIR / "audit_report.txt"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nAudit complete. Saved to: {report_path}")


if __name__ == "__main__":
    run()
