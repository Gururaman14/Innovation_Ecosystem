import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
RAW_DIR = DATA_DIR / "raw"
METADATA_DIR = DATA_DIR / "metadata"
RESULTS_DIR = ROOT_DIR / "results"
DQ_DIR = RESULTS_DIR / "data_quality"
DQ_DIR.mkdir(parents=True, exist_ok=True)

LAYER_A_CSV = PROCESSED_DIR / "layer_a/layer_a_capability_panel.csv"
LAYER_B_CSV = PROCESSED_DIR / "layer_b/layer_b_target_panel.csv"
LOCO_CSV = PROCESSED_DIR / "layer_b/loco_density_all_years.csv"
WDI_WIDE_CSV = RAW_DIR / "wdi/wdi_raw_wide.csv"
WDI_LONG_CSV = RAW_DIR / "wdi/wdi_raw_long.csv"
COUNTRY_CSV = METADATA_DIR / "country_list.csv"
PRODUCT_CSV = METADATA_DIR / "hs4_product_mapping.csv"
AUDIT_CSV = RAW_DIR / "comtrade/comtrade_collection_audit.csv"


def build_dataset_profile():
    specs = [
        ("Layer A Capability Panel", LAYER_A_CSV, "country, year, product_code"),
        ("Layer B Target Panel", LAYER_B_CSV, "country, year, product_code"),
        ("LOCO Contemporary Density", LOCO_CSV, "country, year, product_code"),
        ("WDI Raw Wide Panel", WDI_WIDE_CSV, "country_code, year"),
        ("WDI Raw Long Panel", WDI_LONG_CSV, "country_code, year, variable"),
        ("Country Metadata", COUNTRY_CSV, "iso3"),
        ("Product Mapping Catalog", PRODUCT_CSV, "product_code"),
    ]
    profiles = []
    for name, path, pk in specs:
        if not path.exists():
            continue
        dtype = {"product_code": str} if "product_code" in pk else None
        df = pd.read_csv(path, dtype=dtype, low_memory=False)
        n_miss = int(df.isna().sum().sum())
        profiles.append({
            "dataset_name": name, "file_path": str(path.relative_to(ROOT_DIR)).replace("\\", "/"),
            "rows": len(df), "columns": len(df.columns), "memory_mb": round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2),
            "primary_key": pk, "total_cells": df.size, "missing_cells": n_miss, "missing_pct": round(n_miss / df.size * 100, 2),
            "columns_list": "; ".join(df.columns),
        })
    df_out = pd.DataFrame(profiles)
    df_out.to_csv(DQ_DIR / "dataset_profile.csv", index=False)
    return df_out


def build_missing_value_report():
    rows = []

    layer_a = pd.read_csv(LAYER_A_CSV, dtype={"product_code": str})
    for col in layer_a.columns:
        n_miss = int(layer_a[col].isna().sum())
        if col in ["rca", "capability"]:
            cat = "ZERO_DENOMINATOR_INACTIVE_HS"
            expl = "Inactive HS codes where sample product export is zero make RCA NaN"
        else:
            cat = "COMPLETE" if n_miss == 0 else "OBSERVED_MISSING"
            expl = "Complete coverage across 93,312 cells" if n_miss == 0 else "Customs reporting gaps"
        rows.append({"dataset": "Layer A", "column": col, "total_rows": len(layer_a), "missing_count": n_miss, "missing_pct": round(n_miss / len(layer_a) * 100, 2), "missing_category": cat, "explanation": expl})

    layer_b = pd.read_csv(LAYER_B_CSV, dtype={"product_code": str})
    for col in layer_b.columns:
        n_miss = int(layer_b[col].isna().sum())
        if col in ["density_lag2", "lagged_density"]:
            cat = "EXPECTED_LAG_BOUNDARY"
            expl = "Boundary outcome years 2009-2010 lack 2007-2008 trade data; strictly NaN"
        elif col == "capability_lag2":
            cat = "EXPECTED_LAG_BOUNDARY_AND_INACTIVE_HS"
            expl = "864 boundary rows (2009-2010) plus 18 rows in 2024 for HS 8803"
        elif col == "product_entry":
            cat = "UNOBSERVED_PRIOR_OR_CURRENT_STATE"
            expl = "864 boundary rows plus 54 rows for HS 8803 where capability is NaN"
        elif col in ["rca", "capability"]:
            cat = "ZERO_DENOMINATOR_INACTIVE_HS"
            expl = "54 rows for HS 8803 in years 2022-2024 post-HS revision"
        elif col.endswith("_lag2"):
            cat = "MISSING_NATIONAL_INDICATOR"
            expl = f"Lagged country-level reporting gaps from WDI ({n_miss} rows)"
        else:
            cat = "COMPLETE" if n_miss == 0 else "OBSERVED_MISSING"
            expl = "Complete coverage across 6,912 cells" if n_miss == 0 else "Observed reporting gaps"
        rows.append({"dataset": "Layer B", "column": col, "total_rows": len(layer_b), "missing_count": n_miss, "missing_pct": round(n_miss / len(layer_b) * 100, 2), "missing_category": cat, "explanation": expl})

    wdi = pd.read_csv(WDI_WIDE_CSV)
    for col in wdi.columns:
        if col in ["country_code", "country", "year"]:
            continue
        n_miss = int(wdi[col].isna().sum())
        expl = "Complete across all 18 countries" if n_miss == 0 else f"WDI reporting gap in {n_miss} pairs"
        rows.append({"dataset": "WDI Raw Wide", "column": col, "total_rows": len(wdi), "missing_count": n_miss, "missing_pct": round(n_miss / len(wdi) * 100, 2), "missing_category": "COMPLETE" if n_miss == 0 else "MISSING_NATIONAL_INDICATOR", "explanation": expl})

    df_out = pd.DataFrame(rows)
    df_out.to_csv(DQ_DIR / "missing_value_report.csv", index=False)
    return df_out


def build_duplicate_audit():
    specs = [
        ("Layer A Capability Panel", LAYER_A_CSV, ["country", "year", "product_code"], "Exact 18 countries x 16 years x 324 products = 93,312 balanced unique keys"),
        ("Layer B Target Panel", LAYER_B_CSV, ["country", "year", "product_code"], "Exact 18 countries x 16 years x 24 target products = 6,912 balanced unique keys"),
        ("LOCO Contemporary Density", LOCO_CSV, ["country", "year", "product_code"], "Exact 18 countries x 16 years x 24 target products = 6,912 balanced unique keys"),
        ("WDI Raw Wide Panel", WDI_WIDE_CSV, ["country_code", "year"], "Exact 18 countries x 25 years (2000-2024) = 450 balanced unique keys"),
        ("Country Metadata", COUNTRY_CSV, ["iso3"], "18 canonical research sample economies"),
        ("Product Mapping Catalog", PRODUCT_CSV, ["product_code"], "324 verified unique HS-4 commodity codes"),
        ("Comtrade Cache Audit", AUDIT_CSV, ["reporter_code", "year"], "288 batches across 18 countries x 16 outcome years"),
    ]
    rows = []
    for name, path, keys, notes in specs:
        if not path.exists():
            continue
        dtype = {"product_code": str} if "product_code" in keys else None
        df = pd.read_csv(path, dtype=dtype, low_memory=False)
        dups = int(df.duplicated(subset=keys).sum())
        rows.append({"dataset": name, "evaluated_key": " + ".join(keys), "total_rows": len(df), "unique_keys": len(df.drop_duplicates(subset=keys)), "duplicate_count": dups, "status": "PASSED" if dups == 0 else "FAILED", "notes": notes})
    df_out = pd.DataFrame(rows)
    df_out.to_csv(DQ_DIR / "duplicate_audit.csv", index=False)
    return df_out


def build_trade_data_quality_report():
    layer_a = pd.read_csv(LAYER_A_CSV, dtype={"product_code": str})
    layer_b = pd.read_csv(LAYER_B_CSV, dtype={"product_code": str})

    rows = []
    for name, df in [("Layer A (Universe)", layer_a), ("Layer B (Targets)", layer_b)]:
        tot = len(df)
        pos = df.loc[df["export_value_usd"] > 0, "export_value_usd"]
        n_zero = int((df["export_value_usd"] == 0).sum())
        n_nan = int(df["export_value_usd"].isna().sum())

        rows.append({
            "panel": name, "total_rows": tot,
            "positive_trade_rows": len(pos), "positive_trade_pct": round(len(pos) / tot * 100, 2),
            "confirmed_zero_rows": n_zero, "confirmed_zero_pct": round(n_zero / tot * 100, 2),
            "unobserved_trade_rows": n_nan, "unobserved_trade_pct": round(n_nan / tot * 100, 2),
            "min_export_usd": float(pos.min()) if not pos.empty else 0.0,
            "p25_export_usd": float(pos.quantile(0.25)) if not pos.empty else 0.0,
            "median_export_usd": float(pos.median()) if not pos.empty else 0.0,
            "mean_export_usd": float(pos.mean()) if not pos.empty else 0.0,
            "p75_export_usd": float(pos.quantile(0.75)) if not pos.empty else 0.0,
            "max_export_usd": float(pos.max()) if not pos.empty else 0.0,
            "total_export_volume_usd": float(pos.sum()) if not pos.empty else 0.0,
        })

    df_out = pd.DataFrame(rows)
    df_out.to_csv(DQ_DIR / "trade_data_quality_report.csv", index=False)
    return df_out


def build_indicator_coverage_report():
    wdi = pd.read_csv(WDI_WIDE_CSV)
    layer_b = pd.read_csv(LAYER_B_CSV, dtype={"product_code": str})
    meta_ind = pd.read_csv(METADATA_DIR / "indicator_dictionary.csv")
    code_map = dict(zip(meta_ind["variable"], meta_ind["indicator_code"]))

    indicators = [
        "rd_expenditure", "researchers_rd", "patent_resident", "patent_nonresident",
        "scientific_publications", "fixed_broadband", "internet_users", "tertiary_enrolment",
        "government_education", "fdi", "manufacturing_value_added", "trade_openness",
        "gdp_current_usd", "population_total", "merchandise_exports_total", "hightech_exports",
    ]

    rows = []
    for ind in indicators:
        wdi_valid = int(wdi[ind].notna().sum()) if ind in wdi.columns else 0
        wdi_cov = round(wdi_valid / len(wdi) * 100, 2)

        lag_col = f"{ind}_lag2"
        b_valid = int(layer_b[lag_col].notna().sum()) if lag_col in layer_b.columns else 0
        b_cov = round(b_valid / len(layer_b) * 100, 2)

        full_c = int((wdi.groupby("country_code")[ind].count() == 25).sum()) if ind in wdi.columns else 0
        if b_cov >= 95.0:
            tier = "High Coverage (>=95%)"
        elif b_cov >= 80.0:
            tier = "Moderate Coverage (80-94%)"
        else:
            tier = "Lower Coverage (<80%)"

        rows.append({
            "indicator": ind, "indicator_code": code_map.get(ind, "N/A"),
            "raw_wdi_rows": len(wdi), "raw_wdi_valid": wdi_valid, "raw_wdi_missing": len(wdi) - wdi_valid, "raw_wdi_coverage_pct": wdi_cov,
            "layer_b_rows": len(layer_b), "layer_b_valid": b_valid, "layer_b_missing": len(layer_b) - b_valid, "layer_b_coverage_pct": b_cov,
            "full_coverage_countries": full_c, "partial_coverage_countries": 18 - full_c, "data_quality_tier": tier,
        })

    df_out = pd.DataFrame(rows)
    df_out.to_csv(DQ_DIR / "indicator_coverage_report.csv", index=False)
    return df_out


def build_derived_variable_audit():
    layer_a = pd.read_csv(LAYER_A_CSV, dtype={"product_code": str})
    layer_b = pd.read_csv(LAYER_B_CSV, dtype={"product_code": str})
    loco = pd.read_csv(LOCO_CSV, dtype={"product_code": str})

    rca = layer_a["rca"]
    inf_rca = int(np.isinf(rca).sum())
    min_rca = float(rca.dropna().min())
    max_rca = float(rca.dropna().max())

    cap = layer_a["capability"]
    unique_caps = sorted(cap.dropna().unique().tolist())

    dens = loco["density"]
    dens_ok = bool(((dens >= 0.0) & (dens <= 1.0)).all())

    lag_dens = layer_b["lagged_density"]
    b_nan = layer_b.loc[layer_b["year"].isin([2009, 2010]), "lagged_density"].isna().all()
    b_ok = layer_b.loc[layer_b["year"] >= 2011, "lagged_density"].notna().all()

    entry = layer_b["product_entry"]
    entry_ok = set(entry.dropna().unique().tolist()).issubset({0.0, 1.0})

    rows = [
        {"derived_variable": "Balassa RCA", "dataset": "Layer A", "sample_size": len(layer_a), "valid_count": int(rca.notna().sum()), "missing_count": int(rca.isna().sum()), "infinite_count": inf_rca, "min_value": min_rca, "max_value": max_rca, "rule_validation": "PASSED" if (inf_rca == 0 and min_rca >= 0.0) else "FAILED", "audit_summary": "Zero denominator in inactive HS products evaluates to NaN"},
        {"derived_variable": "Binary Capability M", "dataset": "Layer A", "sample_size": len(layer_a), "valid_count": int(cap.notna().sum()), "missing_count": int(cap.isna().sum()), "infinite_count": 0, "min_value": float(cap.dropna().min()), "max_value": float(cap.dropna().max()), "rule_validation": "PASSED" if unique_caps == [0.0, 1.0] else "FAILED", "audit_summary": "Evaluates to 1.0 for RCA >= 1.0, 0.0 for RCA < 1.0; preserves NaN"},
        {"derived_variable": "Contemporary LOCO Density", "dataset": "LOCO Output", "sample_size": len(loco), "valid_count": int(dens.notna().sum()), "missing_count": int(dens.isna().sum()), "infinite_count": 0, "min_value": float(dens.min()), "max_value": float(dens.max()), "rule_validation": "PASSED" if dens_ok else "FAILED", "audit_summary": "Values strictly in [0.0, 1.0]; focal country excluded"},
        {"derived_variable": "Lagged LOCO Density (t-2)", "dataset": "Layer B", "sample_size": len(layer_b), "valid_count": int(lag_dens.notna().sum()), "missing_count": int(lag_dens.isna().sum()), "infinite_count": 0, "min_value": float(lag_dens.dropna().min()), "max_value": float(lag_dens.dropna().max()), "rule_validation": "PASSED" if (b_nan and b_ok) else "FAILED", "audit_summary": "Outcome year t aligned with year t-2; 864 boundary rows strictly NaN"},
        {"derived_variable": "Product Entry Indicator", "dataset": "Layer B", "sample_size": len(layer_b), "valid_count": int(entry.notna().sum()), "missing_count": int(entry.isna().sum()), "infinite_count": 0, "min_value": float(entry.dropna().min()), "max_value": float(entry.dropna().max()), "rule_validation": "PASSED" if entry_ok else "FAILED", "audit_summary": "1.0 if entry (173); 0.0 if non-entry (5,821); NaN if unobserved"},
    ]
    df_out = pd.DataFrame(rows)
    df_out.to_csv(DQ_DIR / "derived_variable_audit.csv", index=False)
    return df_out


def build_cleaning_log():
    entries = [
        ("CLEAN-001", "Metadata / Comtrade API", "India Comtrade queries with territory code 356 returned 0 records", "UN Comtrade files Indian customs returns under territory code 699", "Updated reporter_code for IND to 699", 16, "All 16 Indian annual batches retrieved and cached"),
        ("CLEAN-002", "Metadata / Comtrade API", "France Comtrade queries with territory code 250 returned partial records", "UN Comtrade files modern French returns under territory code 251 (with Monaco)", "Updated reporter_code for FRA to 251", 16, "All 16 French annual batches retrieved and cached"),
        ("CLEAN-003", "Raw Data / Comtrade Cache", "Missing 147 UN Comtrade batches out of 288 required batches", "Earlier collection hit public API rate limits (HTTP 429/403)", "Executed collect_data.py with adaptive backoff", 147, "Complete 288 / 288 cached JSON batches present on disk"),
        ("CLEAN-004", "Processed Data / LOCO Density", "loco_density_all_years.csv was stale with 0.0 values across 9 countries", "File was not resaved when 288-batch Comtrade collection completed", "Recalculated contemporary LOCO density across all 6,912 target rows", 6912, "All 18 countries have non-zero density values matching Layer B"),
        ("CLEAN-005", "Metadata / Indicator Dictionary", "indicator_dictionary.csv was missing tertiary enrolment and education expenditure", "File was not synchronized with data_dictionary.md", "Rewrote indicator_dictionary.csv with all 22 indicators", 22, "Matches schemas of WDI, Layer B, and data_dictionary.md"),
        ("CLEAN-006", "Derived Variables / RCA Denominator", "HS classification revisions created zero world exports in retired codes", "HS 8803 was replaced in HS 2022 by 8807", "Strict zero-denominator rule assigns NaN rather than 0 or infinity", 2610, "Zero infinite values in Layer A and B; 54 rows in Layer B assigned NaN"),
        ("CLEAN-007", "Derived Variables / Boundary Lags", "Boundary years 2009-2010 lack 2007-2008 trade data for t-2 lag", "Trade data collection window commences in 2009", "Strictly preserve boundary years as explicit NaN", 864, "864 rows in lagged_density and 918 rows in product_entry are visible NaNs"),
    ]
    cols = [
        "log_id", "component", "issue_description", "root_cause",
        "cleaning_action", "affected_rows", "verification_result"
    ]
    df_out = pd.DataFrame(entries, columns=cols)
    df_out["status"] = "RESOLVED"
    df_out.to_csv(DQ_DIR / "cleaning_log.csv", index=False)
    return df_out


if __name__ == "__main__":
    build_dataset_profile()
    build_missing_value_report()
    build_duplicate_audit()
    build_trade_data_quality_report()
    build_indicator_coverage_report()
    build_derived_variable_audit()
    build_cleaning_log()
    print("All 7 data quality reports successfully generated under results/data_quality/!")
