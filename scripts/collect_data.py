import concurrent.futures
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import pandas as pd
import requests

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
METADATA_DIR = DATA_DIR / "metadata"
COMTRADE_CACHE_DIR = DATA_DIR / "raw" / "comtrade" / "cache"
COMTRADE_AUDIT_FILE = DATA_DIR / "raw" / "comtrade" / "comtrade_collection_audit.csv"
WDI_DIR = DATA_DIR / "raw" / "wdi"

COMTRADE_URL = os.environ.get("COMTRADE_BASE_URL", "https://comtradeapi.un.org/public/v1/preview/C/A/HS")
WDI_URL = "https://api.worldbank.org/v2"

COUNTRIES = [
    "USA", "DEU", "JPN", "FRA", "GBR", "KOR", "SGP", "ISR", "NLD", "IRL",
    "CHN", "IND", "BRA", "MEX", "POL", "CZE", "TUR", "MYS"
]

WDI_INDICATORS = {
    "rd_expenditure": "GB.XPD.RSDV.GD.ZS", "researchers_rd": "SP.POP.SCIE.RD.P6",
    "patent_resident": "IP.PAT.RESD", "patent_nonresident": "IP.PAT.NRES",
    "scientific_publications": "IP.JRN.ARTC.SC", "fixed_broadband": "IT.NET.BBND.P2",
    "internet_users": "IT.NET.USER.ZS", "tertiary_enrolment": "SE.TER.ENRR",
    "government_education": "SE.XPD.TOTL.GD.ZS", "fdi": "BX.KLT.DINV.WD.GD.ZS",
    "manufacturing_value_added": "NV.IND.MANF.ZS", "trade_openness": "NE.TRD.GNFS.ZS",
    "gdp_current_usd": "NY.GDP.MKTP.CD", "population_total": "SP.POP.TOTL",
    "merchandise_exports_total": "TX.VAL.MRCH.CD.WT", "hightech_exports": "TX.VAL.TECH.MF.ZS",
}


def load_country_metadata():
    path = METADATA_DIR / "country_list.csv"
    if path.exists():
        df = pd.read_csv(path)
        return dict(zip(df["iso3"], df["reporter_code"]))
    return {
        "USA": 842, "DEU": 276, "JPN": 392, "FRA": 251, "GBR": 826, "KOR": 410,
        "SGP": 702, "ISR": 376, "NLD": 528, "IRL": 372, "CHN": 156, "IND": 699,
        "BRA": 76,  "MEX": 484, "POL": 616, "CZE": 203, "TUR": 792, "MYS": 458
    }


def load_product_codes():
    path = METADATA_DIR / "hs4_product_mapping.csv"
    if path.exists():
        df = pd.read_csv(path, dtype={"product_code": str, "hs4_code": str})
        col = "product_code" if "product_code" in df.columns else "hs4_code"
        return sorted(df[col].astype(str).str.zfill(4).unique().tolist())
    return []


def check_local_cache():
    comtrade_files = list(COMTRADE_CACHE_DIR.glob("*.json")) if COMTRADE_CACHE_DIR.exists() else []
    wdi_file = WDI_DIR / "wdi_raw_wide.csv"
    print(f"Comtrade JSON cache batches on disk: {len(comtrade_files)}")
    if wdi_file.exists():
        df_wdi = pd.read_csv(wdi_file)
        n_c = df_wdi['country_code'].nunique()
        y_min, y_max = df_wdi['year'].min(), df_wdi['year'].max()
        print(f"WDI dataset on disk: {len(df_wdi)} rows ({n_c} countries, {y_min}-{y_max})")
    else:
        print("WDI dataset on disk: Not found")
    return comtrade_files


def fetch_comtrade_batch(reporter_code, year, product_codes=None, use_cache=True, max_retries=3):
    COMTRADE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = COMTRADE_CACHE_DIR / f"comtrade_{reporter_code}_{year}.json"

    if use_cache and cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                records = data.get("data", [])
                cnt = data.get("count", len(records))
                status = "CACHED" if cnt > 0 else "EMPTY_200"
                return records, status, "Loaded from valid local cache"
        except Exception:
            pass

    if product_codes is None:
        product_codes = load_product_codes()

    cmd_string = ",".join(product_codes) + ",TOTAL" if product_codes else "TOTAL"
    params = {"reporterCode": reporter_code, "period": year, "cmdCode": cmd_string, "flowCode": "X", "partnerCode": 0, "partner2Code": 0, "customsCode": "C00", "motCode": 0}
    headers = {"Accept": "application/json", "User-Agent": "Mozilla/5.0"}
    api_key = os.environ.get("COMTRADE_API_KEY")
    if api_key:
        headers["Ocp-Apim-Subscription-Key"] = api_key

    for attempt in range(max_retries):
        try:
            resp = requests.get(COMTRADE_URL, params=params, headers=headers, timeout=40)
            if resp.status_code == 200:
                body = resp.json()
                records = body.get("data", [])
                tmp_file = COMTRADE_CACHE_DIR / f"comtrade_{reporter_code}_{year}.json.tmp"
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump({"reporterCode": reporter_code, "period": year, "retrieved_utc": datetime.now(timezone.utc).isoformat(), "count": len(records), "data": records}, f, indent=1)
                os.replace(tmp_file, cache_file)
                
                status = "SUCCESS" if len(records) > 0 else "EMPTY_200"
                if len(records) > 0:
                    note = f"Retrieved {len(records)} records"
                else:
                    note = "Valid response with 0 reported records"
                return records, status, note
                
            elif resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    wait_sec = float(retry_after) + 0.5
                else:
                    wait_sec = (attempt + 1) * 3.0
                time.sleep(wait_sec)
                
            elif resp.status_code == 403:
                retry_after = resp.headers.get("Retry-After", "unknown")
                note = f"Quota Exceeded (Retry-After: {retry_after}s)"
                return [], "FAILED_QUOTA", note
                
            else:
                note = f"HTTP {resp.status_code}: {resp.reason}"
                if resp.status_code in [500, 502, 503, 504]:
                    time.sleep((attempt + 1) * 2.0)
                else:
                    return [], f"FAILED_HTTP_{resp.status_code}", note
                    
        except requests.exceptions.RequestException as exc:
            time.sleep((attempt + 1) * 2.5)
            if attempt == max_retries - 1:
                return [], "FAILED_ERROR", str(exc)

    return [], "FAILED_RETRIES_EXCEEDED", "Max retries exceeded"


def collect_all_comtrade(countries=COUNTRIES, years=None, delay=1.5):
    if years is None:
        years = list(range(2009, 2025))

    rep_map = load_country_metadata()
    product_codes = load_product_codes()
    audit_rows = []
    quota_exhausted = False
    quota_note = ""

    print(
        f"Collecting Comtrade: {len(countries)} countries x {len(years)} years "
        f"({len(product_codes)} products + TOTAL)..."
    )

    newly_collected = 0
    cached_count = 0
    failed_count = 0

    for c in countries:
        rep = rep_map.get(c)
        if not rep:
            continue
        for y in years:
            cache_file = COMTRADE_CACHE_DIR / f"comtrade_{rep}_{y}.json"
            
            if quota_exhausted and not cache_file.exists():
                audit_rows.append({"country_code": c, "reporter_code": rep, "year": y, "status": "FAILED_QUOTA", "records_count": 0, "notes": quota_note, "timestamp_utc": datetime.now(timezone.utc).isoformat()})
                failed_count += 1
                continue

            records, status, note = fetch_comtrade_batch(rep, y, product_codes=product_codes, use_cache=True)
            
            if status in ["CACHED", "EMPTY_200"] and cache_file.exists():
                cached_count += 1
            elif status in ["SUCCESS", "EMPTY_200"]:
                newly_collected += 1
                print(f"[{status:7s}] {c} ({rep}) {y}: {len(records)} records ({note})")
            elif status == "FAILED_QUOTA":
                quota_exhausted = True
                quota_note = note
                failed_count += 1
                print(f"[QUOTA EXHAUSTED] {c} ({rep}) {y}: {note}. Pausing collection to protect existing data.")
            else:
                failed_count += 1
                print(f"[{status:7s}] {c} ({rep}) {y}: {note}")

            audit_rows.append({"country_code": c, "reporter_code": rep, "year": y, "status": status, "records_count": len(records), "notes": note, "timestamp_utc": datetime.now(timezone.utc).isoformat()})

            if status in ["SUCCESS", "EMPTY_200"] and not cache_file.exists():
                time.sleep(delay)

    COMTRADE_AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(audit_rows).to_csv(COMTRADE_AUDIT_FILE, index=False)
    print("Comtrade Collection Summary:")
    print(f"  Pre-existing cached batches: {cached_count}")
    print(f"  Newly collected batches:     {newly_collected}")
    print(f"  Total valid on disk:         {cached_count + newly_collected}")
    print(f"  Failed / Quota-blocked:      {failed_count}")
    print(f"Authoritative audit saved to: {COMTRADE_AUDIT_FILE}")
    return audit_rows


def fetch_wdi_series(country_code, variable_name, indicator_code, start_year=2000, end_year=2024):
    url = f"{WDI_URL}/country/{country_code}/indicator/{indicator_code}"
    params = {"format": "json", "per_page": 100, "date": f"{start_year}:{end_year}"}
    for attempt in range(3):
        try:
            resp = requests.get(url, params=params, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) >= 2 and data[1]:
                    records = []
                    for row in data[1]:
                        if row.get("date"):
                            records.append({"country_code": country_code, "country": row.get("country", {}).get("value", country_code), "year": int(row["date"]), "variable": variable_name, "indicator": indicator_code, "value": row.get("value")})
                    return records
            time.sleep(1)
        except Exception:
            time.sleep(2)
    return []


def collect_all_wdi(countries=COUNTRIES, indicators=WDI_INDICATORS, start_year=2000, end_year=2024, max_workers=8):
    WDI_DIR.mkdir(parents=True, exist_ok=True)
    tasks = [(c, var, ind) for c in countries for var, ind in indicators.items()]
    print(f"Querying World Bank WDI ({len(tasks)} queries across {len(countries)} countries)...")

    all_records = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(fetch_wdi_series, c, var, ind, start_year, end_year) for c, var, ind in tasks]
        for f in concurrent.futures.as_completed(futures):
            res = f.result()
            if res:
                all_records.extend(res)

    df_long = pd.DataFrame(all_records)
    df_long.to_csv(WDI_DIR / "wdi_raw_long.csv", index=False)

    wide = df_long.pivot_table(index=["country_code", "country", "year"], columns="variable", values="value").reset_index()
    wide.columns.name = None
    wide = wide.sort_values(["country_code", "year"]).reset_index(drop=True)
    wide.to_csv(WDI_DIR / "wdi_raw_wide.csv", index=False)

    n_c = wide['country_code'].nunique()
    print(f"WDI collection complete. Saved {len(wide)} wide rows across {n_c} countries.")
    return wide


def load_existing_wdi():
    wdi_path = WDI_DIR / "wdi_raw_wide.csv"
    if wdi_path.exists():
        return pd.read_csv(wdi_path)
    return None


def load_clean_patents():
    wipo_path = DATA_DIR / "raw" / "wipo" / "wipo_patents_clean_2000_2024.csv"
    if wipo_path.exists():
        return pd.read_csv(wipo_path)
    return None


if __name__ == "__main__":
    print("Checking local data cache...")
    check_local_cache()
    wdi = load_existing_wdi()
    if wdi is None or wdi["country_code"].nunique() < 18:
        print("Collecting complete WDI dataset for all 18 countries...")
        collect_all_wdi()
    else:
        n_c = wdi['country_code'].nunique()
        print(f"Loaded existing WDI dataset: {wdi.shape[0]} rows, {n_c} countries.")
