import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
METADATA_DIR = DATA_DIR / "metadata"
COMTRADE_CACHE_DIR = DATA_DIR / "raw" / "comtrade" / "cache"
PROCESSED_DIR = DATA_DIR / "processed"
LAYER_A_DIR = PROCESSED_DIR / "layer_a"
LAYER_B_DIR = PROCESSED_DIR / "layer_b"

COUNTRIES = [
    "USA", "DEU", "JPN", "FRA", "GBR", "KOR", "SGP", "ISR", "NLD", "IRL",
    "CHN", "IND", "BRA", "MEX", "POL", "CZE", "TUR", "MYS"
]
YEARS = list(range(2009, 2025))


def load_country_metadata():
    path = METADATA_DIR / "country_list.csv"
    if path.exists():
        df = pd.read_csv(path)
        code_to_iso = dict(zip(df["reporter_code"], df["iso3"]))
        iso_to_name = dict(zip(df["iso3"], df["country"]))
        return code_to_iso, iso_to_name
    return {}, {}


def load_product_catalog():
    path = METADATA_DIR / "hs4_product_mapping.csv"
    if path.exists():
        df = pd.read_csv(path, dtype={"product_code": str, "hs4_code": str})
        code_col = "product_code" if "product_code" in df.columns else "hs4_code"
        name_col = "product_name" if "product_name" in df.columns else "hs4_description"
        cat_col = "category" if "category" in df.columns else "sector"
        tgt_col = "is_target" if "is_target" in df.columns else "is_target_product"

        df["product_code"] = df[code_col].astype(str).str.zfill(4)
        df["product_name"] = df[name_col]
        df["category"] = df[cat_col]
        df["is_target"] = pd.to_numeric(df[tgt_col], errors="coerce").fillna(0).astype(int)
        cols = ["product_code", "product_name", "category", "is_target"]
        return df[cols].drop_duplicates("product_code")
    return pd.DataFrame()


def load_raw_comtrade_records(cache_dir=COMTRADE_CACHE_DIR):
    code_to_iso, _ = load_country_metadata()
    if not cache_dir.exists():
        return pd.DataFrame(), pd.DataFrame()

    cache_files = list(cache_dir.glob("comtrade_*.json"))
    if not cache_files:
        return pd.DataFrame(), pd.DataFrame()

    trade_records = []
    total_records = []

    for f in cache_files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                content = json.load(fp)
        except Exception:
            continue

        rep = content.get("reporterCode")
        yr = content.get("period")
        iso = code_to_iso.get(rep, str(rep))
        rows = content.get("data", [])

        for r in rows:
            cmd = str(r.get("cmdCode", "")).strip()
            val = r.get("primaryValue")
            flow = r.get("flowCode")
            partner = r.get("partnerCode")
            partner2 = r.get("partner2Code", 0)

            if flow != "X" or partner != 0:
                continue

            try:
                val_flt = float(val) if val is not None else np.nan
            except (ValueError, TypeError):
                val_flt = np.nan

            if cmd == "TOTAL":
                total_records.append({"country": iso, "year": int(yr), "total_merchandise_exports_usd": val_flt, "partner2Code": partner2})
            else:
                code_4d = cmd.split(".")[0].strip().zfill(4)
                trade_records.append({"country": iso, "year": int(yr), "product_code": code_4d, "export_value_usd": val_flt, "partner2Code": partner2})

    trade_df = pd.DataFrame(trade_records)
    totals_df = pd.DataFrame(total_records)

    if not totals_df.empty:
        totals_df = (
            totals_df.sort_values(["country", "year", "partner2Code"])
            .drop_duplicates(subset=["country", "year"], keep="first")[["country", "year", "total_merchandise_exports_usd"]]
        )

    if not trade_df.empty:
        sort_cols = ["country", "year", "product_code", "partner2Code", "export_value_usd"]
        trade_df = (
            trade_df.sort_values(sort_cols, ascending=[True, True, True, True, False])
            .drop_duplicates(subset=["country", "year", "product_code"], keep="first")[["country", "year", "product_code", "export_value_usd"]]
        )

    return trade_df, totals_df


def load_wdi_export_totals():
    wdi_path = DATA_DIR / "raw" / "wdi" / "wdi_raw_wide.csv"
    if wdi_path.exists():
        df = pd.read_csv(wdi_path)
        if "merchandise_exports_total" in df.columns:
            return df[["country_code", "year", "merchandise_exports_total"]].rename(
                columns={"country_code": "country", "merchandise_exports_total": "wdi_total_exports_usd"}
            )
    return pd.DataFrame()


def create_layer_a_grid(countries=COUNTRIES, years=YEARS, product_catalog=None):
    if product_catalog is None or product_catalog.empty:
        product_catalog = load_product_catalog()

    product_codes = product_catalog["product_code"].tolist()
    grid = [{"country": c, "year": y, "product_code": p} for c in countries for y in years for p in product_codes]
    return pd.DataFrame(grid)


def compile_layer_a(trade_data=None, totals_data=None, countries=COUNTRIES, years=YEARS):
    catalog = load_product_catalog()
    if catalog.empty:
        raise ValueError("Product catalog is empty. Verify data/metadata/hs4_product_mapping.csv.")

    grid = create_layer_a_grid(countries=countries, years=years, product_catalog=catalog)

    if trade_data is None or totals_data is None:
        t_data, tot_data = load_raw_comtrade_records()
        trade_data = t_data if trade_data is None else trade_data
        totals_data = tot_data if totals_data is None else totals_data

    if not trade_data.empty:
        layer_a = grid.merge(trade_data, on=["country", "year", "product_code"], how="left")
    else:
        layer_a = grid.copy()
        layer_a["export_value_usd"] = np.nan

    reporting_cy = set()
    if not trade_data.empty:
        reporting_cy.update(set(zip(trade_data["country"], trade_data["year"].astype(int))))
    if not totals_data.empty:
        reporting_cy.update(set(zip(totals_data["country"], totals_data["year"].astype(int))))

    is_reporting = layer_a.apply(lambda r: (r["country"], int(r["year"])) in reporting_cy, axis=1)
    status_series = pd.Series(index=layer_a.index, dtype=str)
    status_series[~is_reporting] = "UNAVAILABLE_YEAR"
    status_series[is_reporting & (layer_a["export_value_usd"] > 0)] = "POSITIVE"
    zero_mask = is_reporting & (layer_a["export_value_usd"].isna() | (layer_a["export_value_usd"] == 0))
    status_series[zero_mask] = "CONFIRMED_ZERO"
    
    layer_a.loc[status_series == "CONFIRMED_ZERO", "export_value_usd"] = 0.0
    layer_a["Trade_Status"] = status_series

    wdi_totals = load_wdi_export_totals()
    if not totals_data.empty:
        layer_a = layer_a.merge(totals_data, on=["country", "year"], how="left")
    else:
        layer_a["total_merchandise_exports_usd"] = np.nan

    if not wdi_totals.empty:
        layer_a = layer_a.merge(wdi_totals, on=["country", "year"], how="left")
        layer_a["total_merchandise_exports_usd"] = layer_a["total_merchandise_exports_usd"].combine_first(layer_a["wdi_total_exports_usd"])
        layer_a = layer_a.drop(columns=["wdi_total_exports_usd"], errors="ignore")

    cat_cols = ["product_code", "product_name", "category", "is_target"]
    layer_a = layer_a.merge(catalog[cat_cols], on="product_code", how="left")
    return layer_a


def extract_layer_b(layer_a):
    layer_b = layer_a[layer_a["is_target"] == 1].copy().reset_index(drop=True)
    layer_b = layer_b.rename(columns={"category": "sector"})
    return layer_b


def save_processed_datasets(layer_a, layer_b):
    LAYER_A_DIR.mkdir(parents=True, exist_ok=True)
    LAYER_B_DIR.mkdir(parents=True, exist_ok=True)

    layer_a_file = LAYER_A_DIR / "layer_a_capability_panel.csv"
    layer_b_file = LAYER_B_DIR / "layer_b_target_panel.csv"

    layer_a.to_csv(layer_a_file, index=False)
    layer_b.to_csv(layer_b_file, index=False)

    print(f"Saved Layer A capability panel ({len(layer_a)} rows) to {layer_a_file}")
    print(f"Saved Layer B target panel ({len(layer_b)} rows) to {layer_b_file}")


if __name__ == "__main__":
    catalog = load_product_catalog()
    print(f"Catalog loaded: {len(catalog)} total products ({catalog['is_target'].sum()} targets)")
    grid = create_layer_a_grid(product_catalog=catalog)
    print(f"Rectangular Layer A grid: {len(grid)} rows (expected: 18 x 16 x 324 = 93,312)")
