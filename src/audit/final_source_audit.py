import sys
from io import StringIO
from pathlib import Path
import pandas as pd
import requests

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import COMTRADE_CODES, COUNTRIES, SOURCES_AUDIT_DIR, STUDY_END, STUDY_START

WB_INDICATORS = {
    "High-tech exports": "TX.VAL.TECH.MF.ZS",
    "R&D expenditure": "GB.XPD.RSDV.GD.ZS",
    "Researchers in R&D": "SP.POP.SCIE.RD.P6",
    "Patent applications - residents": "IP.PAT.RESD",
    "Patent applications - non-residents": "IP.PAT.NRES",
    "Internet users": "IT.NET.USER.ZS",
    "Fixed broadband": "IT.NET.BBND.P2",
    "Tertiary enrolment": "SE.TER.ENRR",
    "Government education expenditure": "SE.XPD.TOTL.GD.ZS",
    "FDI": "BX.KLT.DINV.WD.GD.ZS",
    "Manufacturing value added": "NV.IND.MANF.ZS",
}


def run_final_source_audit():
    SOURCES_AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    results = []

    def record(var, source, country, code, status, earliest=None, latest=None, n_years=None, notes=""):
        results.append({
            "Variable": var, "Source": source, "Country": country, "Code": code,
            "Status": status, "Earliest": earliest, "Latest": latest, "Years": n_years, "Notes": notes
        })

    # World Bank baseline
    for var, ind in WB_INDICATORS.items():
        for country, code in COUNTRIES.items():
            url = f"https://api.worldbank.org/v2/country/{code}/indicator/{ind}?format=json&per_page=100"
            try:
                resp = requests.get(url, timeout=30)
                data = resp.json()
                if len(data) < 2 or not data[1]:
                    record(var, "World Bank", country, code, "NO DATA")
                    continue
                years = [
                    int(item["date"]) for item in data[1]
                    if item.get("value") is not None and STUDY_START <= int(item["date"]) <= STUDY_END
                ]
                if years:
                    record(var, "World Bank", country, code, "AVAILABLE", min(years), max(years), len(years))
                else:
                    record(var, "World Bank", country, code, "NO DATA")
            except Exception as exc:
                record(var, "World Bank", country, code, f"ERROR: {exc}")

    # Comtrade
    for country, code in COUNTRIES.items():
        rep_code = COMTRADE_CODES[code]
        comtrade_url = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
        years = []
        for y in range(STUDY_START, STUDY_END + 1):
            params = {"reporterCode": rep_code, "period": y, "flowCode": "X", "partnerCode": 0, "maxRecords": 1}
            try:
                r = requests.get(comtrade_url, params=params, timeout=20)
                if r.status_code == 200 and r.json().get("data"):
                    years.append(y)
            except Exception:
                continue
        status = "AVAILABLE" if years else "NO DATA"
        record("High-tech exports", "UN Comtrade", country, code, status,
               min(years) if years else None, max(years) if years else None, len(years))

    out_df = pd.DataFrame(results)
    out_file = SOURCES_AUDIT_DIR / "FINAL_SOURCE_COVERAGE_AUDIT.csv"
    out_df.to_csv(out_file, index=False)
    print(f"Final source audit complete. Saved to: {out_file}")


if __name__ == "__main__":
    run_final_source_audit()
