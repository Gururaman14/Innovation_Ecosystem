import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd

sys.path.append(str(Path(__file__).resolve().parent))

from capability_analysis import (
    calculate_rca, calculate_capability,
    calculate_loco_proximity, calculate_density
)
from build_panel import align_lagged_density, add_product_entry, merge_national_indicators

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RESULTS_DIR = ROOT_DIR / "results"
METADATA_DIR = DATA_DIR / "metadata"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
VALIDATION_DIR = RESULTS_DIR / "validation"

EXPECTED_COUNTRIES = [
    "USA", "DEU", "JPN", "FRA", "GBR", "KOR", "SGP", "ISR", "NLD", "IRL",
    "CHN", "IND", "BRA", "MEX", "POL", "CZE", "TUR", "MYS"
]
EXPECTED_SECTORS = [
    "Advanced Industrial Machinery", "Aerospace", "Computers and Electronics",
    "Electrical Machinery", "Pharmaceuticals", "Scientific and Medical Instruments",
    "Telecommunications and Electronics"
]


def audit_metadata():
    results = {}

    c_file = METADATA_DIR / "country_list.csv"
    if c_file.exists():
        df_c = pd.read_csv(c_file)
        iso_list = df_c["iso3"].dropna().tolist()
        missing = [c for c in EXPECTED_COUNTRIES if c not in iso_list]
        passed = (len(iso_list) == 18 and not missing and "IRL" in iso_list and "SWE" not in iso_list)
        results["country_metadata"] = {"status": "PASSED" if passed else "FAILED", "countries_count": len(iso_list), "expected_count": 18, "missing_countries": missing, "ireland_present": "IRL" in iso_list}
    else:
        results["country_metadata"] = {"status": "FAILED", "reason": "country_list.csv missing"}

    p_file = METADATA_DIR / "hs4_product_mapping.csv"
    if p_file.exists():
        df_p = pd.read_csv(p_file, dtype={"product_code": str, "hs4_code": str})
        code_col = "product_code" if "product_code" in df_p.columns else "hs4_code"
        tgt_col = "is_target" if "is_target" in df_p.columns else "is_target_product"
        cat_col = "category" if "category" in df_p.columns else "sector"

        total_prods = len(df_p)
        targets = df_p[pd.to_numeric(df_p[tgt_col], errors="coerce") == 1]
        target_count = len(targets)
        target_sectors = sorted(targets[cat_col].dropna().unique().tolist())
        dups = int(df_p[code_col].duplicated().sum())
        all_valid_codes = df_p[code_col].apply(lambda x: len(str(x)) == 4 and str(x).isdigit()).all()

        passed = (total_prods == 324 and target_count == 24 and target_sectors == EXPECTED_SECTORS and dups == 0 and all_valid_codes)
        results["product_catalog"] = {"status": "PASSED" if passed else "FAILED", "total_products": total_prods, "target_products": target_count, "sectors_count": len(target_sectors), "sectors_match": target_sectors == EXPECTED_SECTORS, "duplicate_codes": dups, "all_4digit_numeric": bool(all_valid_codes)}
    else:
        results["product_catalog"] = {"status": "FAILED", "reason": "hs4_product_mapping.csv missing"}

    return results


def audit_raw_datasets():
    results = {}

    wdi_file = RAW_DIR / "wdi" / "wdi_raw_wide.csv"
    if wdi_file.exists():
        df_wdi = pd.read_csv(wdi_file)
        c_found = df_wdi["country_code"].unique().tolist() if "country_code" in df_wdi.columns else []
        missing_c = [c for c in EXPECTED_COUNTRIES if c not in c_found]
        y_min = int(df_wdi["year"].min()) if "year" in df_wdi.columns else None
        y_max = int(df_wdi["year"].max()) if "year" in df_wdi.columns else None
        has_total = "merchandise_exports_total" in df_wdi.columns
        passed = (len(missing_c) == 0 and len(df_wdi) >= 288 and has_total)
        results["wdi_raw_data"] = {"status": "PASSED" if passed else "FAILED", "rows": len(df_wdi), "countries_count": len(c_found), "missing_countries": missing_c, "year_range": f"{y_min}-{y_max}", "merchandise_exports_total_present": has_total}
    else:
        results["wdi_raw_data"] = {"status": "NOT_RUN", "reason": "wdi_raw_wide.csv not found on disk"}

    cache_dir = RAW_DIR / "comtrade" / "cache"
    if cache_dir.exists():
        batches = list(cache_dir.glob("*.json"))
        audit_file = RAW_DIR / "comtrade" / "comtrade_collection_audit.csv"
        audit_count = len(pd.read_csv(audit_file)) if audit_file.exists() else 0
        b_status = "PASSED" if len(batches) >= 288 else ("IN_PROGRESS" if len(batches) > 0 else "EMPTY")
        results["comtrade_cache"] = {"status": b_status, "cached_batches": len(batches), "expected_batches": 288, "audit_records": audit_count}
    else:
        results["comtrade_cache"] = {"status": "NOT_RUN", "reason": "Comtrade cache directory not found"}

    return results


def run_algorithmic_unit_tests():
    results = {}

    test_trade = pd.DataFrame([
        {"country": "USA", "year": 2020, "product_code": "8471", "export_value_usd": 100.0, "total_merchandise_exports_usd": 1000.0},
        {"country": "USA", "year": 2020, "product_code": "8802", "export_value_usd": 200.0, "total_merchandise_exports_usd": 1000.0},
        {"country": "KOR", "year": 2020, "product_code": "8471", "export_value_usd": 150.0, "total_merchandise_exports_usd": 500.0},
        {"country": "KOR", "year": 2020, "product_code": "8802", "export_value_usd": 50.0,  "total_merchandise_exports_usd": 500.0},
        {"country": "BRA", "year": 2020, "product_code": "8471", "export_value_usd": 0.0,   "total_merchandise_exports_usd": 0.0},
    ])
    rca_res = calculate_rca(test_trade)
    no_inf = not np.isinf(rca_res["rca"].dropna()).any()
    bra_is_nan = rca_res.loc[rca_res["country"] == "BRA", "rca"].isna().all()
    usa_rca = rca_res.loc[rca_res["country"] == "USA", "rca"].values[0]
    rca_correct = np.isclose(usa_rca, 0.60, atol=1e-3)
    results["rca_calculation_and_safety"] = {"status": "PASSED" if (no_inf and bra_is_nan and rca_correct) else "FAILED", "infinite_values_absent": no_inf, "zero_denominator_assigned_nan": bra_is_nan, "formula_accurate": bool(rca_correct)}

    cap_res = calculate_capability(rca_res)
    caps = cap_res["capability"].dropna().tolist()
    only_binary = all(c in [0.0, 1.0] for c in caps)
    bra_cap_nan = cap_res.loc[cap_res["country"] == "BRA", "capability"].isna().all()
    results["capability_classification"] = {"status": "PASSED" if (only_binary and bra_cap_nan) else "FAILED", "strictly_binary": only_binary, "missing_rca_preserves_nan": bra_cap_nan}

    test_loco = pd.DataFrame([
        {"country": "C1", "year": 2020, "product_code": "P1", "capability": 1.0},
        {"country": "C1", "year": 2020, "product_code": "P2", "capability": 1.0},
        {"country": "C2", "year": 2020, "product_code": "P1", "capability": 1.0},
        {"country": "C2", "year": 2020, "product_code": "P2", "capability": 0.0},
        {"country": "C3", "year": 2020, "product_code": "P1", "capability": 0.0},
        {"country": "C3", "year": 2020, "product_code": "P2", "capability": 1.0},
    ])
    loco_proxs = calculate_loco_proximity(test_loco, year=2020)
    c1_phi = loco_proxs["C1"]
    c1_excluded = (c1_phi.loc["P1", "P2"] == 0.0)
    symmetric = np.allclose(c1_phi.values, c1_phi.values.T)
    results["loco_proximity_properties"] = {"status": "PASSED" if (c1_excluded and symmetric) else "FAILED", "focal_country_strictly_excluded": c1_excluded, "matrix_symmetric": bool(symmetric)}

    dens_res = calculate_density(test_loco, target_products=["P1", "P2"], year=2020)
    in_range = ((dens_res["density"] >= 0.0) & (dens_res["density"] <= 1.0)).all()
    results["density_properties"] = {"status": "PASSED" if in_range else "FAILED", "densities_in_range_0_1": bool(in_range), "target_count": len(dens_res)}

    test_grid = pd.DataFrame([{"country": "USA", "year": y, "product_code": "P1"} for y in range(2009, 2013)])
    test_dens = pd.DataFrame([{"country": "USA", "year": y, "product_code": "P1", "density": 0.5} for y in range(2009, 2013)])
    lag_res = align_lagged_density(test_grid, test_dens, lag=2)
    b_2009 = np.isnan(lag_res.loc[lag_res["year"] == 2009, "lagged_density"].values[0])
    b_2010 = np.isnan(lag_res.loc[lag_res["year"] == 2010, "lagged_density"].values[0])
    b_2011 = lag_res.loc[lag_res["year"] == 2011, "lagged_density"].values[0] == 0.5
    results["lag_boundary_visibility"] = {"status": "PASSED" if (b_2009 and b_2010 and b_2011) else "FAILED", "boundary_strictly_nan": bool(b_2009 and b_2010), "post_boundary_aligned": bool(b_2011)}

    test_entry = pd.DataFrame([
        {"country": "USA", "year": 2009, "product_code": "P1", "capability": 0.0},
        {"country": "USA", "year": 2011, "product_code": "P1", "capability": 1.0},
        {"country": "USA", "year": 2009, "product_code": "P2", "capability": 0.0},
        {"country": "USA", "year": 2011, "product_code": "P2", "capability": 0.0},
    ])
    e_res = add_product_entry(test_entry, lag=2)
    e_2009_nan = np.isnan(e_res.loc[e_res["year"] == 2009, "product_entry"].values[0])
    e_2011_p1 = (e_res.loc[(e_res["year"] == 2011) & (e_res["product_code"] == "P1"), "product_entry"].values[0] == 1.0)
    e_2011_p2 = (e_res.loc[(e_res["year"] == 2011) & (e_res["product_code"] == "P2"), "product_entry"].values[0] == 0.0)
    results["product_entry_rules"] = {"status": "PASSED" if (e_2009_nan and e_2011_p1 and e_2011_p2) else "FAILED", "missing_lag_gives_nan": bool(e_2009_nan), "entry_event_detected": bool(e_2011_p1), "non_entry_is_zero": bool(e_2011_p2)}

    return results


def audit_empirical_panels():
    results = {}

    layer_a_file = PROCESSED_DIR / "layer_a" / "layer_a_capability_panel.csv"
    if layer_a_file.exists():
        df_a = pd.read_csv(layer_a_file, dtype={"product_code": str})
        rows_a = len(df_a)
        dups_a = int(df_a.duplicated(subset=["country", "year", "product_code"]).sum())
        expected_a = 18 * 16 * 324
        passed_a = (rows_a == expected_a and dups_a == 0)
        ts_counts_a = df_a["Trade_Status"].value_counts().to_dict() if "Trade_Status" in df_a.columns else {}
        results["layer_a_empirical_panel"] = {"status": "PASSED" if passed_a else "FAILED", "rows": rows_a, "expected_rows": expected_a, "duplicates": dups_a, "countries": df_a["country"].nunique(), "years": df_a["year"].nunique(), "products": df_a["product_code"].nunique(), "trade_status_counts": ts_counts_a}
    else:
        results["layer_a_empirical_panel"] = {"status": "NOT_RUN", "reason": "layer_a_capability_panel.csv not yet generated on disk"}

    layer_b_file = PROCESSED_DIR / "layer_b" / "layer_b_target_panel.csv"
    if layer_b_file.exists():
        df_b = pd.read_csv(layer_b_file, dtype={"product_code": str})
        rows_b = len(df_b)
        dups_b = int(df_b.duplicated(subset=["country", "year", "product_code"]).sum())
        expected_b = 18 * 16 * 24
        passed_b = (rows_b == expected_b and dups_b == 0)
        
        ts_counts_b = df_b["Trade_Status"].value_counts().to_dict() if "Trade_Status" in df_b.columns else {}
        entry_series = df_b["product_entry"].fillna("MISSING_LAG").astype(str)
        entry_status_counts = entry_series.value_counts().to_dict()
        
        crosstab_df = pd.crosstab(df_b["Trade_Status"], entry_series, margins=True)
        crosstab_dict = crosstab_df.to_dict()
        n_entries = int((df_b["product_entry"] == 1.0).sum()) if "product_entry" in df_b.columns else 0

        results["layer_b_empirical_panel"] = {"status": "PASSED" if passed_b else "FAILED", "rows": rows_b, "expected_rows": expected_b, "duplicates": dups_b, "countries": df_b["country"].nunique(), "years": df_b["year"].nunique(), "products": df_b["product_code"].nunique(), "trade_status_counts": ts_counts_b, "entry_status_counts": entry_status_counts, "cross_tabulation": crosstab_dict, "entries_observed": n_entries}
    else:
        results["layer_b_empirical_panel"] = {"status": "NOT_RUN", "reason": "layer_b_target_panel.csv not yet generated on disk"}

    layer_a_grav_file = PROCESSED_DIR / "layer_a" / "layer_a_gravity_panel.csv"
    if layer_a_grav_file.exists():
        df_grav = pd.read_csv(layer_a_grav_file, dtype={"product_code": str})
        rows_grav = len(df_grav)
        dups_grav = int(df_grav.duplicated(subset=["country", "year", "product_code"]).sum())
        expected_a = 18 * 16 * 324
        passed_grav = (rows_grav == expected_a and dups_grav == 0 and "lagged_density" in df_grav.columns and "rd_expenditure_lag2" in df_grav.columns)
        results["layer_a_gravity_panel"] = {"status": "PASSED" if passed_grav else "FAILED", "rows": rows_grav, "expected_rows": expected_a, "duplicates": dups_grav, "has_lagged_density": "lagged_density" in df_grav.columns, "has_rd_lag2": "rd_expenditure_lag2" in df_grav.columns}
    else:
        results["layer_a_gravity_panel"] = {"status": "NOT_RUN", "reason": "layer_a_gravity_panel.csv not yet generated on disk"}

    return results


def run_full_validation():
    print("Research pipeline validation audit:")

    print("Metadata checks:")
    meta = audit_metadata()
    for k, v in meta.items():
        print(f"[{v['status']:11s}] {k}: {v}")

    print("Raw dataset audits:")
    raw = audit_raw_datasets()
    for k, v in raw.items():
        print(f"[{v['status']:11s}] {k}: {v}")

    print("Algorithmic unit tests:")
    algo = run_algorithmic_unit_tests()
    all_algo_passed = True
    for k, v in algo.items():
        print(f"[{v['status']:11s}] {k}")
        if v["status"] != "PASSED":
            all_algo_passed = False

    print("Empirical panel audits:")
    panels = audit_empirical_panels()
    for k, v in panels.items():
        print(f"[{v['status']:11s}] {k}: {v.get('status')} (Rows: {v.get('rows', 'N/A')})")
    
    if (
        "layer_b_empirical_panel" in panels and
        "cross_tabulation" in panels["layer_b_empirical_panel"]
    ):
        print("Layer B count reconciliation:")
        xtab = panels["layer_b_empirical_panel"]["cross_tabulation"]
        xtab_df = pd.DataFrame(xtab)
        print(xtab_df.to_string())

    print(f"Algorithmic Unit Tests Passed: {all_algo_passed}")

    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "metadata_checks": meta,
        "raw_dataset_audits": raw,
        "algorithmic_unit_tests": algo,
        "all_algorithmic_tests_passed": all_algo_passed,
        "empirical_panel_audits": panels
    }
    with open(VALIDATION_DIR / "validation_report.json", "w", encoding="utf-8") as fp:
        json.dump(
            report, fp, indent=2,
            default=lambda x: bool(x) if isinstance(x, (np.bool_, bool)) else str(x)
        )

    summary_file = RESULTS_DIR / "validation_summary.json"
    checks_passed = sum(1 for d in [meta, raw, algo, panels] for v in d.values() if isinstance(v, dict) and v.get("status") == "PASSED")
    total_checks = sum(1 for d in [meta, raw, algo, panels] for v in d.values() if isinstance(v, dict) and "status" in v)
    concise_summary = {
        "status": "PASSED" if all_algo_passed and checks_passed == total_checks else "FAILED",
        "checks_passed": checks_passed,
        "checks_failed": total_checks - checks_passed,
        "total_checks": total_checks,
        "all_algorithmic_tests_passed": all_algo_passed,
        "panel_dimensions": {
            "layer_a_rows": panels.get("layer_a_empirical_panel", {}).get("rows"),
            "layer_b_rows": panels.get("layer_b_empirical_panel", {}).get("rows"),
            "layer_a_gravity_rows": panels.get("layer_a_gravity_panel", {}).get("rows")
        }
    }
    with open(summary_file, "w", encoding="utf-8") as fp:
        json.dump(concise_summary, fp, indent=2)

    out_file = VALIDATION_DIR / 'validation_report.json'
    print(f"Authoritative validation report saved to: {out_file}")
    print(f"Concise validation summary saved to: {summary_file}")
    return report


if __name__ == "__main__":
    run_full_validation()
