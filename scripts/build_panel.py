import numpy as np
import pandas as pd
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
WDI_PATH = DATA_DIR / "raw" / "wdi" / "wdi_raw_wide.csv"


def align_lagged_density(target_panel, density_data, lag=2):
    if density_data is None or density_data.empty:
        df = target_panel.copy()
        df["lagged_density"] = np.nan
        return df

    donor = density_data[["country", "year", "product_code", "density"]].copy()
    donor["year"] = donor["year"] + lag
    donor = donor.rename(columns={"density": f"density_lag{lag}"})

    merged = target_panel.merge(donor, on=["country", "year", "product_code"], how="left")
    merged["lagged_density"] = merged[f"density_lag{lag}"]
    return merged


def add_product_entry(target_panel, lag=2):
    df = target_panel.copy()
    if "capability" not in df.columns:
        df["product_entry"] = np.nan
        return df

    donor = df[["country", "year", "product_code", "capability"]].copy()
    donor["year"] = donor["year"] + lag
    donor = donor.rename(columns={"capability": f"capability_lag{lag}"})

    merged = df.merge(donor, on=["country", "year", "product_code"], how="left")
    lag_cap = merged[f"capability_lag{lag}"]
    cur_cap = merged["capability"]
    valid = lag_cap.notna() & cur_cap.notna()

    entry = np.full(len(merged), np.nan)
    at_risk = valid & (lag_cap == 0.0)
    entry[at_risk & (cur_cap == 1.0)] = 1.0
    entry[at_risk & (cur_cap == 0.0)] = 0.0

    merged["product_entry"] = entry
    return merged


def merge_national_indicators(target_panel, national_data=None, lag=2):
    if national_data is None:
        if not WDI_PATH.exists():
            return target_panel
        national_data = pd.read_csv(WDI_PATH)

    donor = national_data.copy()
    c_col = "country_code" if "country_code" in donor.columns else "country"
    donor["year"] = donor["year"] + lag

    skip = {"country", "country_code", "year"}
    cols = [c for c in donor.columns if c not in skip]
    donor = donor[[c_col, "year"] + cols].rename(columns={c: f"{c}_lag{lag}" for c in cols})
    merged = target_panel.merge(donor, left_on=["country", "year"], right_on=[c_col, "year"], how="left")
    if c_col in merged.columns and c_col != "country":
        merged = merged.drop(columns=[c_col])

    return merged


def build_complete_panel(target_data, density_data=None, national_data=None, lag=2):
    panel = align_lagged_density(target_data, density_data, lag=lag)
    panel = add_product_entry(panel, lag=lag)
    panel = merge_national_indicators(panel, national_data, lag=lag)
    sort_cols = [c for c in ["country", "year", "product_code"] if c in panel.columns]
    return panel.sort_values(sort_cols).reset_index(drop=True)


if __name__ == "__main__":
    test_grid = pd.DataFrame([{"country": "USA", "year": y, "product_code": "8471", "capability": 1.0 if y >= 2011 else 0.0} for y in range(2009, 2014)])
    test_dens = pd.DataFrame([{"country": "USA", "year": y, "product_code": "8471", "density": 0.4 + y * 0.05} for y in range(2009, 2014)])
    res = build_complete_panel(test_grid, test_dens, lag=2)

    PROCESSED_B = DATA_DIR / "processed" / "layer_b"
    PROCESSED_A = DATA_DIR / "processed" / "layer_a"
    WEEK5_PANELS = ROOT_DIR / "results" / "week5" / "panels"
    WEEK5_AUDIT = ROOT_DIR / "results" / "week5" / "audit"
    WEEK5_PANELS.mkdir(parents=True, exist_ok=True)
    WEEK5_AUDIT.mkdir(parents=True, exist_ok=True)

    layer_a_file = PROCESSED_A / "layer_a_capability_panel.csv"
    loco_file = PROCESSED_B / "loco_density_all_years.csv"

    if layer_a_file.exists() and loco_file.exists() and WDI_PATH.exists():
        df_a = pd.read_csv(layer_a_file, dtype={"product_code": str})
        df_a["product_code"] = df_a["product_code"].astype(str).str.zfill(4)
        targets = df_a[df_a["is_target"] == 1].copy().reset_index(drop=True)
        if "category" in targets.columns and "sector" not in targets.columns:
            targets = targets.rename(columns={"category": "sector"})

        df_dens = pd.read_csv(loco_file, dtype={"product_code": str})
        df_dens["product_code"] = df_dens["product_code"].astype(str).str.zfill(4)
        df_wdi = pd.read_csv(WDI_PATH)

        layer_b_rebuilt = build_complete_panel(targets, df_dens, df_wdi, lag=2)
        out_b = PROCESSED_B / "layer_b_target_panel.csv"
        layer_b_rebuilt.to_csv(out_b, index=False)

        total_rows = len(layer_b_rebuilt)
        boundary_rows = int(layer_b_rebuilt["year"].isin([2009, 2010]).sum())
        valid_trans = layer_b_rebuilt["capability_lag2"].notna() & layer_b_rebuilt["capability"].notna()
        inactive_rows = int(((layer_b_rebuilt["year"] >= 2011) & ~valid_trans).sum())
        trans_rows = layer_b_rebuilt[valid_trans].copy()
        n_trans = len(trans_rows)
        n_incumbents = int((trans_rows["capability_lag2"] == 1.0).sum())
        at_risk = trans_rows[trans_rows["capability_lag2"] == 0.0].copy()
        n_at_risk = len(at_risk)
        n_events_at_risk = int((at_risk["product_entry"] == 1.0).sum())
        n_events_total = n_events_at_risk

        at_risk_complete = at_risk[at_risk["rd_expenditure_lag2"].notna()].copy()
        n_at_risk_complete = len(at_risk_complete)
        n_events_complete = int((at_risk_complete["product_entry"] == 1.0).sum())

        flow_data = [
            {"step": 1, "stage": "Total Structural Grid", "rows": total_rows, "events": np.nan, "rate_pct": np.nan, "notes": "18 economies x 24 focal products x 16 years (2009-2024)"},
            {"step": 2, "stage": "Lag Boundary Rows (2009-2010)", "rows": boundary_rows, "events": np.nan, "rate_pct": np.nan, "notes": "No t-2 trade data; lag strictly unobserved"},
            {"step": 3, "stage": "Inactive HS Nomenclature Rows", "rows": inactive_rows, "events": np.nan, "rate_pct": np.nan, "notes": "HS 8803 deleted in 2022 WCO revision; RCA/capability NaN"},
            {"step": 4, "stage": "Observed 2-Year Transitions", "rows": n_trans, "events": n_events_total, "rate_pct": round(n_events_total / n_trans * 100, 3), "notes": "Effective estimation window 2011-2024"},
            {"step": 5, "stage": "Baseline Incumbents (M_{t-2} = 1)", "rows": n_incumbents, "events": 0, "rate_pct": 0.0, "notes": "Already specialized at baseline; ineligible for entry"},
            {"step": 6, "stage": "At-Risk Candidate Population (M_{t-2} = 0)", "rows": n_at_risk, "events": n_events_at_risk, "rate_pct": round(n_events_at_risk / n_at_risk * 100, 3), "notes": "Primary estimation sample for discrete entry"},
            {"step": 7, "stage": "Complete-Case At-Risk Sample (with R&D)", "rows": n_at_risk_complete, "events": n_events_complete, "rate_pct": round(n_events_complete / n_at_risk_complete * 100, 3), "notes": "100 missing R&D rows (MYS: 56, IND: 44)"}
        ]

        df_flow = pd.DataFrame(flow_data)
        df_flow.to_csv(WEEK5_PANELS / "sample_flow_summary.csv", index=False)
        df_flow.to_csv(WEEK5_AUDIT / "sample_flow_summary.csv", index=False)

        at_risk.to_csv(WEEK5_PANELS / "layer_b_at_risk_panel.csv", index=False)
        at_risk_complete.to_csv(WEEK5_PANELS / "layer_b_at_risk_complete.csv", index=False)
        trans_rows.to_csv(WEEK5_PANELS / "layer_b_transition_panel.csv", index=False)
