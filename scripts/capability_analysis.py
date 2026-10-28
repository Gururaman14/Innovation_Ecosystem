import numpy as np
import pandas as pd


def calculate_rca(df, country_col="country", year_col="year", product_col="product_code",
                  export_col="export_value_usd", total_export_col="total_merchandise_exports_usd"):
    data = df.copy()
    data[export_col] = pd.to_numeric(data[export_col], errors="coerce")

    if total_export_col in data.columns and data[total_export_col].notna().any():
        data[total_export_col] = pd.to_numeric(data[total_export_col], errors="coerce")
        country_tot = data[total_export_col]
        c_totals = (
            data[[country_col, year_col, total_export_col]]
            .drop_duplicates(subset=[country_col, year_col])
            .groupby(year_col)[total_export_col]
            .sum(min_count=1)
            .rename("_grand_sample_total")
        )
        data = data.merge(c_totals, on=year_col, how="left")
        grand_tot = data["_grand_sample_total"]
    else:
        country_tot = data.groupby([country_col, year_col])[export_col].transform("sum")
        grand_tot = data.groupby(year_col)[export_col].transform("sum")

    product_tot = data.groupby([year_col, product_col])[export_col].transform("sum")

    valid_country_share = (country_tot > 0) & data[export_col].notna() & (data[export_col] >= 0)
    valid_sample_share = (grand_tot > 0) & (product_tot > 0)

    country_share = np.where(valid_country_share, data[export_col] / country_tot, np.nan)
    sample_share = np.where(valid_sample_share, product_tot / grand_tot, np.nan)

    valid_rca = (sample_share > 0) & ~np.isnan(country_share)
    rca = np.where(valid_rca, country_share / sample_share, np.nan)

    if "_grand_sample_total" in data.columns:
        data = data.drop(columns=["_grand_sample_total"])

    data["rca"] = np.where(np.isinf(rca), np.nan, rca)
    return data


def calculate_capability(df, rca_col="rca", threshold=1.0):
    data = df.copy()
    data["capability"] = np.where(data[rca_col].isna(), np.nan, np.where(data[rca_col] >= threshold, 1.0, 0.0))
    return data


def calculate_loco_proximity(df, year, country_col="country", product_col="product_code", capability_col="capability"):
    sub = df[df["year"] == year].copy()
    if sub.empty:
        return {}

    pivot = sub.pivot(index=country_col, columns=product_col, values=capability_col).fillna(0.0)
    countries = list(pivot.index)
    products = list(pivot.columns)

    loco_proximities = {}
    for focal_country in countries:
        ref_matrix = pivot.drop(index=focal_country).values
        co_occur = ref_matrix.T @ ref_matrix
        ubiquity = np.diag(co_occur)
        max_ubiq = np.maximum(ubiquity[:, None], ubiquity[None, :])

        with np.errstate(divide="ignore", invalid="ignore"):
            phi = np.where(max_ubiq > 0, co_occur / max_ubiq, 0.0)

        np.fill_diagonal(phi, 1.0)
        phi = np.clip(phi, 0.0, 1.0)
        loco_proximities[focal_country] = pd.DataFrame(phi, index=products, columns=products)

    return loco_proximities


def calculate_density(df, target_products, year, country_col="country", product_col="product_code", capability_col="capability"):
    loco_dict = calculate_loco_proximity(df, year, country_col, product_col, capability_col)
    if not loco_dict:
        return pd.DataFrame()

    sub = df[df["year"] == year]
    pivot = sub.pivot(index=country_col, columns=product_col, values=capability_col).fillna(0.0)
    all_products = list(pivot.columns)

    rows = []
    for country, phi_df in loco_dict.items():
        if country not in pivot.index:
            continue
        c_caps = pivot.loc[country]

        for target in target_products:
            if target not in phi_df.index:
                continue

            neigh_prods = [p for p in all_products if p != target and p in phi_df.columns]
            if not neigh_prods:
                omega = 0.0
            else:
                proximities = phi_df.loc[target, neigh_prods].values
                caps = c_caps[neigh_prods].values
                denom = np.sum(proximities)
                omega = float(np.sum(caps * proximities) / denom) if denom > 0 else 0.0

            rows.append({"country": country, "year": year, "product_code": target, "density": float(np.clip(omega, 0.0, 1.0))})

    return pd.DataFrame(rows)


def calculate_all_densities(df, target_products, years=None):
    if years is None:
        years = sorted(df["year"].dropna().unique().astype(int).tolist())

    results = []
    for y in years:
        dens = calculate_density(df, target_products, y)
        if not dens.empty:
            results.append(dens)

    return pd.concat(results, ignore_index=True) if results else pd.DataFrame()


if __name__ == "__main__":
    test = pd.DataFrame([
        {"country": "USA", "year": 2020, "product_code": "8471", "export_value_usd": 100.0, "total_merchandise_exports_usd": 1000.0},
        {"country": "USA", "year": 2020, "product_code": "8802", "export_value_usd": 200.0, "total_merchandise_exports_usd": 1000.0},
        {"country": "KOR", "year": 2020, "product_code": "8471", "export_value_usd": 150.0, "total_merchandise_exports_usd": 500.0},
        {"country": "KOR", "year": 2020, "product_code": "8802", "export_value_usd": 50.0, "total_merchandise_exports_usd": 500.0},
        {"country": "BRA", "year": 2020, "product_code": "8471", "export_value_usd": 0.0, "total_merchandise_exports_usd": 0.0},
    ])
    rca_df = calculate_rca(test)
    cap_df = calculate_capability(rca_df)
    print("Test RCA with total merchandise exports:")
    print(cap_df[["country", "year", "product_code", "rca", "capability"]])
