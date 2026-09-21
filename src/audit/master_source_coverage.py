import sys
import time
from pathlib import Path
import pandas as pd
import requests

sys.path.append(str(Path(__file__).resolve().parents[2]))
from src.config import COMTRADE_CODES, COUNTRIES, SOURCES_AUDIT_DIR, STUDY_END, STUDY_START, STUDY_YEARS

TIMEOUT = 45

INDICATOR_SOURCES = {
    "High-tech exports": ["World Bank", "UN Comtrade"],
    "R&D expenditure": ["World Bank", "OECD MSTI", "UNESCO UIS"],
    "Researchers in R&D": ["World Bank", "OECD MSTI", "UNESCO UIS"],
    "Patent applications - residents": ["World Bank", "WIPO"],
    "Patent applications - non-residents": ["World Bank", "WIPO"],
    "Internet users": ["World Bank", "ITU"],
    "Fixed broadband": ["World Bank", "ITU"],
    "Tertiary enrolment": ["World Bank", "UNESCO UIS"],
    "Government education expenditure": ["World Bank", "UNESCO UIS"],
    "FDI": ["World Bank", "UNCTAD"],
    "Manufacturing value added": ["World Bank", "UNIDO"],
}

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


def audit_world_bank():
    print("Auditing World Bank baseline indicators...")
    rows = []
    total_years = len(STUDY_YEARS)

    for var, ind in WB_INDICATORS.items():
        for country, iso3 in COUNTRIES.items():
            url = f"https://api.worldbank.org/v2/country/{iso3}/indicator/{ind}?format=json&per_page=100"
            try:
                resp = requests.get(url, timeout=TIMEOUT)
                if resp.status_code != 200:
                    rows.append({
                        "Source": "World Bank", "Variable": var, "Country": country,
                        "Status": "API_ERROR", "FirstYear": None, "LastYear": None,
                        "YearsAvailable": 0, "CoveragePercent": 0, "MissingYears": ""
                    })
                    continue
                data = resp.json()
                if len(data) < 2 or data[1] is None:
                    rows.append({
                        "Source": "World Bank", "Variable": var, "Country": country,
                        "Status": "NO_DATA", "FirstYear": None, "LastYear": None,
                        "YearsAvailable": 0, "CoveragePercent": 0,
                        "MissingYears": ",".join(map(str, STUDY_YEARS))
                    })
                    continue

                available = {
                    int(item["date"]) for item in data[1]
                    if item.get("date") and item.get("value") is not None
                    and STUDY_START <= int(item["date"]) <= STUDY_END
                }
                missing = [y for y in STUDY_YEARS if y not in available]
                pct = round(len(available) / total_years * 100, 1)

                status = "COMPLETE" if len(available) == total_years else "NO_DATA" if not available else "PARTIAL"
                rows.append({
                    "Source": "World Bank", "Variable": var, "Country": country,
                    "Status": status,
                    "FirstYear": min(available) if available else None,
                    "LastYear": max(available) if available else None,
                    "YearsAvailable": len(available),
                    "CoveragePercent": pct,
                    "MissingYears": ",".join(map(str, missing))
                })
            except Exception:
                rows.append({
                    "Source": "World Bank", "Variable": var, "Country": country,
                    "Status": "ERROR", "FirstYear": None, "LastYear": None,
                    "YearsAvailable": 0, "CoveragePercent": 0, "MissingYears": ""
                })
            time.sleep(0.15)
    return pd.DataFrame(rows)


def run_master_source_audit():
    SOURCES_AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    wb_df = audit_world_bank()

    records = []
    for var, sources in INDICATOR_SOURCES.items():
        for src in sources:
            for country, iso3 in COUNTRIES.items():
                if src == "World Bank":
                    matched = wb_df[(wb_df["Variable"] == var) & (wb_df["Country"] == country)]
                    if not matched.empty:
                        row = matched.iloc[0].to_dict()
                        records.append(row)
                        continue
                records.append({
                    "Source": src,
                    "Variable": var,
                    "Country": country,
                    "Status": "NOT_YET_EXTRACTED",
                    "FirstYear": None,
                    "LastYear": None,
                    "YearsAvailable": 0,
                    "CoveragePercent": 0.0,
                    "MissingYears": f"{STUDY_START}-{STUDY_END}",
                })

    master_df = pd.DataFrame(records)
    master_df.to_csv(SOURCES_AUDIT_DIR / "MASTER_SOURCE_COVERAGE.csv", index=False)

    summary_df = (
        master_df.groupby(["Source", "Status"])
        .size()
        .reset_index(name="Count")
    )
    summary_df.to_csv(SOURCES_AUDIT_DIR / "MASTER_SOURCE_STATUS_SUMMARY.csv", index=False)

    print("\nMaster coverage matrix generated.")
    print(f"Saved to: {SOURCES_AUDIT_DIR}")


if __name__ == "__main__":
    run_master_source_audit()
