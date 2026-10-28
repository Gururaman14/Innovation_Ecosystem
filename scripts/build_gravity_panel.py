import json
from pathlib import Path
import time
import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
PROCESSED_DIR = DATA_DIR / "processed"
LAYER_A_DIR = PROCESSED_DIR / "layer_a"
METADATA_DIR = DATA_DIR / "metadata"
WDI_PATH = DATA_DIR / "raw" / "wdi" / "wdi_raw_wide.csv"
RESULTS_DIR = ROOT_DIR / "results" / "week5"
LOGS_DIR = RESULTS_DIR / "logs"

LOGS_DIR.mkdir(parents=True, exist_ok=True)


def calculate_loco_density_all_products(df_layer_a):
    years = sorted(df_layer_a["year"].dropna().unique().astype(int).tolist())
    all_records = []

    for yr in years:
        sub = df_layer_a[df_layer_a["year"] == yr]
        pivot = sub.pivot(index="country", columns="product_code", values="capability").fillna(0.0)
        countries = list(pivot.index)
        products = list(pivot.columns)

        for focal_country in countries:
            ref_matrix = pivot.drop(index=focal_country).values
            co_occur = ref_matrix.T @ ref_matrix
            ubiquity = np.diag(co_occur)
            max_ubiq = np.maximum(ubiquity[:, None], ubiquity[None, :])

            with np.errstate(divide="ignore", invalid="ignore"):
                phi = np.where(max_ubiq > 0, co_occur / max_ubiq, 0.0)

            np.fill_diagonal(phi, 0.0)
            phi = np.clip(phi, 0.0, 1.0)

            c_caps = pivot.loc[focal_country].values
            num = phi @ c_caps
            denom = phi.sum(axis=1)

            with np.errstate(divide="ignore", invalid="ignore"):
                omega = np.where(denom > 0, num / denom, 0.0)
            omega = np.clip(omega, 0.0, 1.0)

            for p_idx, p_code in enumerate(products):
                all_records.append({
                    "country": focal_country,
                    "year": yr,
                    "product_code": p_code,
                    "density": float(omega[p_idx])
                })

    return pd.DataFrame(all_records)


def align_lagged_features(layer_a_df, density_df, wdi_df, lag=2):
    dens_donor = density_df[["country", "year", "product_code", "density"]].copy()
    dens_donor["year"] = dens_donor["year"] + lag
    dens_donor = dens_donor.rename(columns={"density": f"density_lag{lag}"})

    merged = layer_a_df.merge(dens_donor, on=["country", "year", "product_code"], how="left")
    merged["lagged_density"] = merged[f"density_lag{lag}"]

    c_col = "country_code" if "country_code" in wdi_df.columns else "country"
    wdi_donor = wdi_df.copy()
    wdi_donor["year"] = wdi_donor["year"] + lag

    skip_cols = {"country", "country_code", "year"}
    indicator_cols = [c for c in wdi_donor.columns if c not in skip_cols]
    wdi_donor = wdi_donor[[c_col, "year"] + indicator_cols].rename(
        columns={c: f"{c}_lag{lag}" for c in indicator_cols}
    )

    merged = merged.merge(wdi_donor, left_on=["country", "year"], right_on=[c_col, "year"], how="left")
    if c_col in merged.columns and c_col != "country":
        merged = merged.drop(columns=[c_col])

    merged["log_export_value"] = np.log1p(merged["export_value_usd"].clip(lower=0))
    return merged


def build_gravity_panel(output_path=None):
    layer_a_file = LAYER_A_DIR / "layer_a_capability_panel.csv"
    if not layer_a_file.exists():
        raise FileNotFoundError(f"Layer A base panel missing: {layer_a_file}")

    df_a = pd.read_csv(layer_a_file, dtype={"product_code": str})
    df_a["product_code"] = df_a["product_code"].astype(str).str.zfill(4)

    expected_rows = 18 * 16 * 324
    if len(df_a) != expected_rows:
        raise ValueError(f"Expected {expected_rows} rows in Layer A, found {len(df_a)}")

    df_dens = calculate_loco_density_all_products(df_a)

    if not WDI_PATH.exists():
        raise FileNotFoundError(f"WDI data missing at {WDI_PATH}")
    df_wdi = pd.read_csv(WDI_PATH)

    gravity_df = align_lagged_features(df_a, df_dens, df_wdi, lag=2)

    sort_cols = ["country", "product_code", "year"]
    gravity_df = gravity_df.sort_values(sort_cols).reset_index(drop=True)

    assert len(gravity_df) == expected_rows
    assert gravity_df.duplicated(subset=["country", "year", "product_code"]).sum() == 0

    boundary_mask = gravity_df["year"].isin([2009, 2010])
    assert gravity_df.loc[boundary_mask, "lagged_density"].isna().all()

    if output_path is None:
        output_path = LAYER_A_DIR / "layer_a_gravity_panel.csv"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    gravity_df.to_csv(output_path, index=False)

    summary = {
        "status": "COMPLETED",
        "rows": len(gravity_df),
        "expected_rows": expected_rows,
        "countries": int(gravity_df["country"].nunique()),
        "years": int(gravity_df["year"].nunique()),
        "products": int(gravity_df["product_code"].nunique()),
        "positive_trade_rows": int((gravity_df["export_value_usd"] > 0).sum()),
        "zero_trade_rows": int((gravity_df["export_value_usd"] == 0).sum()),
        "lag_boundary_rows_2009_2010": int(boundary_mask.sum()),
        "estimation_sample_2011_2024": int((~boundary_mask).sum()),
        "rd_missing_estimation_window": int(gravity_df.loc[~boundary_mask, "rd_expenditure_lag2"].isna().sum())
    }

    with open(LOGS_DIR / "build_gravity_panel_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    return gravity_df, summary


if __name__ == "__main__":
    build_gravity_panel()
