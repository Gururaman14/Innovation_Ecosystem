import sys
from io import StringIO
from pathlib import Path
import pandas as pd
import requests

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import COMTRADE_CODES, COUNTRIES, OECD_RAW_DIR, SOURCES_AUDIT_DIR, STUDY_END, STUDY_START


def check_comtrade_years(reporter_code: int):
    available_years = []
    base_url = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
    for year in range(STUDY_START, STUDY_END + 1):
        params = {
            "reporterCode": reporter_code,
            "period": year,
            "flowCode": "X",
            "partnerCode": 0,
            "partner2Code": 0,
            "customsCode": "C00",
            "motCode": 0,
            "maxRecords": 1,
        }
        try:
            resp = requests.get(base_url, params=params, timeout=30)
            if resp.status_code == 200 and resp.json().get("data"):
                available_years.append(year)
        except Exception:
            continue
    return available_years


def run_alternative_sources_audit():
    SOURCES_AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    def record(var, source, country, code, status, earliest=None, latest=None, obs=None, missing_pct=None, notes=""):
        results.append({
            "Variable": var, "Source": source, "Country": country, "Country_Code": code,
            "Status": status, "Earliest_Year": earliest, "Latest_Year": latest,
            "Number_of_Years": obs, "Missing_Percentage": missing_pct, "Notes": notes
        })

    # 1. UN Comtrade
    print("Checking UN Comtrade coverage...")
    for country, code in COUNTRIES.items():
        years = check_comtrade_years(COMTRADE_CODES[code])
        if years:
            record("High-tech exports", "UN Comtrade", country, code, "AVAILABLE",
                   min(years), max(years), len(years), None,
                   "Trade records available. Requires SITC/HS high-tech mapping.")
        else:
            record("High-tech exports", "UN Comtrade", country, code, "NO DATA", notes="No trade records returned.")

    # 2. OECD MSTI
    print("Checking OECD MSTI coverage...")
    oecd_url = "https://sdmx.oecd.org/public/rest/data/OECD.STI.STP,DSD_MSTI@DF_MSTI,1.3/.A.G+T_RS.PT_B1GQ.."
    params = {"startPeriod": STUDY_START, "endPeriod": STUDY_END, "dimensionAtObservation": "AllDimensions"}
    try:
        resp = requests.get(oecd_url, params=params, headers={"Accept": "text/csv"}, timeout=90)
        if resp.status_code == 200:
            oecd = pd.read_csv(StringIO(resp.text))
            OECD_RAW_DIR.mkdir(parents=True, exist_ok=True)
            oecd.to_csv(OECD_RAW_DIR / "oecd_msti_raw.csv", index=False)
            for country, code in COUNTRIES.items():
                subset = oecd[oecd["REF_AREA"].astype(str) == code].copy()
                if subset.empty:
                    continue
                subset["TIME_PERIOD"] = pd.to_numeric(subset["TIME_PERIOD"], errors="coerce")
                subset = subset[subset["TIME_PERIOD"].between(STUDY_START, STUDY_END)]
                for measure in subset["MEASURE"].dropna().unique():
                    m = subset[subset["MEASURE"] == measure]
                    years = m["TIME_PERIOD"].dropna()
                    if len(years) == 0:
                        continue
                    m_str = str(measure).upper()
                    var_name = "R&D expenditure" if "GERD" in m_str else "Researchers in R&D" if "RESEARCH" in m_str else None
                    if not var_name:
                        continue
                    missing_pct = round(100 * (1 - m["OBS_VALUE"].notna().mean()), 2)
                    record(var_name, "OECD MSTI", country, code, "AVAILABLE",
                           int(years.min()), int(years.max()), len(years), missing_pct, "OECD MSTI measure")
    except Exception as exc:
        print(f"OECD query notice: {exc}")

    # 3. UNESCO UIS
    for var in ["Tertiary enrolment", "Government education expenditure"]:
        for country, code in COUNTRIES.items():
            record(var, "UNESCO UIS", country, code, "REQUIRES_INDICATOR_QUERY",
                   notes="UIS API accessible. Indicator mapping required.")

    # 4. WIPO Patents
    for var in ["Patent applications - residents", "Patent applications - non-residents"]:
        for country, code in COUNTRIES.items():
            record(var, "WIPO Statistics Database", country, code, "REQUIRES_DOWNLOAD",
                   notes="Historical patent statistics available. Filing office breakdown required.")

    # 5. ITU DataHub
    for var in ["Internet users", "Fixed broadband"]:
        for country, code in COUNTRIES.items():
            record(var, "ITU DataHub", country, code, "REQUIRES_DATA_EXTRACTION",
                   notes="International ICT benchmark source identified.")

    # 6. UNIDO
    for country, code in COUNTRIES.items():
        record("Manufacturing value added", "UNIDO", country, code, "REQUIRES_API_QUERY",
               notes="UNIDO Statistics Portal API identified.")

    # 7. Venture Capital
    for country, code in COUNTRIES.items():
        record("Venture capital proxy", "OECD / alternative source", country, code, "NOT_SELECTED",
               notes="No proxy finalized pending cross-country comparability review.")

    out_df = pd.DataFrame(results)
    out_path = SOURCES_AUDIT_DIR / "alternative_data_availability_audit_v2.csv"
    out_df.to_csv(out_path, index=False)
    print(f"\nAudit complete. Saved to: {out_path}")


if __name__ == "__main__":
    run_alternative_sources_audit()
