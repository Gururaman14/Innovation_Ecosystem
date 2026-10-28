# National Innovation Ecosystems and High-Technology Product Exports: A Product Space Analysis of 18 Economies (2009–2024)

## Project Overview (Weeks 1–4)

This repository contains the data acquisition, cleaning, network capability calculation, and panel construction pipeline for an empirical study examining how national research and development (R&D) expenditure and product-space capabilities relate to high-technology export diversification.

### Core Research Problem & Objectives (as of Week 4)

A central dilemma in industrial policy and economic complexity is:
> **"Does national R&D spending help countries enter technologically distant high-tech products where they lack prior manufacturing experience (distance-bridging), or does R&D primarily matter when a country already makes related goods nearby in product space (adjacent reinforcement)?"**

To prepare this empirical investigation for econometric estimation, the project establishes a rigorous, dual-layer product space panel across 18 benchmark economies from 2009 to 2024.

---

## Empirical Scope

- **18 Sovereign Economies:**
  - *Advanced Innovators (10):* United States (`USA`), Germany (`DEU`), Japan (`JPN`), France (`FRA`), United Kingdom (`GBR`), South Korea (`KOR`), Singapore (`SGP`), Israel (`ISR`), Netherlands (`NLD`), Ireland (`IRL`).
  - *Major Emerging Economies (8):* China (`CHN`), India (`IND`), Brazil (`BRA`), Mexico (`MEX`), Poland (`POL`), Czechia (`CZE`), Turkey (`TUR`), Malaysia (`MYS`).
- **Time Horizon:** 2009–2024 (16 annual periods), providing a balanced post-financial-crisis panel.
- **Dual-Layer Product Space Architecture:**
  - **Layer A (Network Foundation):** 324 Harmonized System 4-digit (HS-4) manufacturing products covering total manufactured exports across the 18 economies ($18 \times 16 \times 324 = 93,312$ observations). Used to construct the co-occurrence product space network and capability density.
  - **Layer B (Target High-Tech Panel):** 24 focal high-technology product lines across 7 priority industrial sectors ($18 \times 16 \times 24 = 6,912$ observations). Used for discrete product-entry transition analysis.
- **Priority Industrial Sectors (Layer B):**
  1. Advanced Industrial Machinery
  2. Aerospace
  3. Computers and Electronics
  4. Electrical Machinery
  5. Pharmaceuticals
  6. Scientific and Medical Instruments
  7. Telecommunications and Electronics

---

## Work Completed in Weeks 1–4

### Week 1: Data Acquisition & Source Audits
- Initial research design and source coverage audits across international reporting bodies: UN Comtrade, World Bank World Development Indicators (WDI), OECD Main Science and Technology Indicators (MSTI), WIPO Patent Statistics, and UNCTAD/WITS.
- Audited reporter-year availability, historical gaps, and cross-source consistency.

### Week 2: Data Ingestion, Cleaning & Nomenclature Harmonization
- Expanded the analytical cohort to 18 benchmark economies over 2009–2024.
- Implemented `scripts/collect_data.py` to extract bilateral customs records and national macroeconomic series with local disk caching to prevent API rate-limit interruptions.
- Implemented `scripts/prepare_data.py` to assemble the rectangular 93,312-row Layer A grid and extract the 6,912-row Layer B target panel.
- Handled the 2022 World Customs Organization (WCO) HS 8803 $\to$ 8807 aircraft parts nomenclature reclassification, separating structural reclassifications from true trade cessation.
- Implemented `scripts/generate_data_quality_reports.py` to profile missingness, zero trade, and variable completeness.

### Week 3: Product Space & Capability Metrics
- Implemented `scripts/capability_analysis.py` containing core network algorithms:
  1. **Balassa (1965) Revealed Comparative Advantage (RCA):**
     $$\text{RCA}_{cpt} = \frac{X_{cpt} / \sum_{p'} X_{cp't}}{\sum_{c'} X_{c'pt} / \sum_{c', p'} X_{c'p't}}$$
     Normalized using total national merchandise exports from WDI to ensure consistency across reporting regimes.
  2. **Binary Product Capability:**
     $$M_{cpt} = \mathbf{1}(\text{RCA}_{cpt} \ge 1.0)$$
  3. **Leave-One-Country-Out (LOCO) Product Proximity:**
     $$\phi_{pp'}^{-c} = \min \left( P(M_{p'}=1 \mid M_p=1)_{-c}, P(M_p=1 \mid M_{p'}=1)_{-c} \right)$$
     Omits the focal country $c$ when computing the co-occurrence probability matrix, preventing mechanical endogeneity (where a country's own large export basket artificially inflates the proximity between its exported products).
  4. **Capability Density:**
     $$\text{density}_{cpt} = \frac{\sum_{p' \neq p} \phi_{pp'}^{-c} M_{cp't}}{\sum_{p' \neq p} \phi_{pp'}^{-c}} \in [0, 1]$$
     Measures how technologically close an unentered product $p$ is to country $c$'s existing capability basket.

### Week 4: Panel Construction & Structural Validation
- Implemented `scripts/build_panel.py` to assemble the two-year lagged discrete entry panel:
  - Temporal transition steps: $t-2 \to t$ (effective estimation window: 2011–2024).
  - Transition accounting:
    - Total structural grid: **6,912 observations**.
    - Boundary lag rows (2009–2010 lacking $t-2$ trade data): **864 rows**.
    - Inactive HS 8803 post-2021 rows: **54 rows**.
    - Observed two-year transitions: **5,994 observations**.
    - Baseline incumbents ($M_{t-2}=1$): **1,747 observations** (excluded from the risk set).
    - At-risk candidate population ($M_{t-2}=0$): **4,247 observations** (173 entry events).
    - Missing R&D rows dropped under listwise deletion: **100 observations** (56 Malaysia, 44 India).
    - Complete-case estimation sample: **4,147 observations** with **166 entry events** (a 4.003% baseline entry rate).
  - Merged two-year lagged macroeconomic controls: $\ln(\text{GDP})$, trade openness (% of GDP), and R&D expenditure (% of GDP).
- Implemented `scripts/build_gravity_panel.py` to assemble the continuous export gravity panel on dollar export values ($X_{cpt}$).
- Implemented `scripts/validate.py` to run automated unit tests:
  - Validates country metadata (18 countries) and product catalog (324 products, 24 targets, 7 sectors).
  - Algorithmic unit tests for RCA calculation, binary capability classification, LOCO proximity symmetry, density bounds $[0, 1]$, lag boundaries, and product-entry transition accounting.
  - Empirical assertions verifying panel row counts (Layer A: 93,312; Layer B: 6,912).

---

## Repository Structure (Week 4 Snapshot)

```
Innovation_Ecosystem/
├── config.py                                 # Centralized paths, cohort lists, and indicator mappings
├── requirements.txt                          # Python dependencies
├── .gitignore                                # Git ignore rules for caches, temporary files, and later weeks
├── README.md                                 # Project documentation (Weeks 1-4)
├── data/
│   ├── metadata/                             # Harmonized metadata and catalogs
│   │   ├── country_list.csv                  # 18 benchmark economies (ISO-3, names, Comtrade codes)
│   │   ├── hs4_product_mapping.csv           # 324 HS-4 products, 7 sectors, 24 target flags
│   │   └── indicator_dictionary.csv          # Variable dictionary for trade & macro indicators
│   ├── raw/
│   │   └── wdi/
│   │       └── wdi_raw_wide.csv              # World Bank WDI indicators for 18 economies (2000-2024)
│   └── audit/                                # Source coverage audits from Week 1
│       ├── 18_country/                       # Peer country comparison audits
│       ├── comtrade/                         # UN Comtrade availability audits
│       └── sources/                          # Multi-source coverage audits
├── scripts/
│   ├── collect_data.py                       # UN Comtrade API & World Bank WDI data ingestion with caching
│   ├── prepare_data.py                       # Layer A balanced grid assembly and Layer B target extraction
│   ├── generate_data_quality_reports.py     # Data quality, missingness, and reporting consistency profiling
│   ├── capability_analysis.py                # Balassa RCA, LOCO proximity matrices, and capability density
│   ├── build_panel.py                        # Layer B 2-year lagged entry panel & transition accounting
│   ├── build_gravity_panel.py                # Layer A continuous export gravity panel construction
│   └── validate.py                           # Algorithmic unit tests and panel structural validation
└── src/                                      # Week 1 exploratory audit and extraction routines
    ├── config.py                             # Week 1 configuration
    ├── audit/                                # Week 1 source audits
    ├── extraction/                           # Week 1 data extractors
    └── processing/                           # Week 1 gap analysis
```

---

## Environment & Requirements

- **Python Version:** Python 3.10+ recommended (verified on Python 3.14.2).
- **Core Dependencies:**
  - `numpy >= 1.24.0`
  - `pandas >= 2.0.0`
  - `requests >= 2.31.0`
  - `scipy >= 1.10.0`
  - `statsmodels >= 0.14.0`
  - `openpyxl >= 3.1.0`
  - `tabulate >= 0.9.0`
  - `matplotlib >= 3.7.0`
  - `seaborn >= 0.12.0`

Install dependencies via:
```bash
pip install -r requirements.txt
```

---

## Running the Week 1–4 Pipeline

### 1. Run Pipeline Validation and Unit Tests
To verify metadata catalogs, algorithmic correctness, and panel structural assertions:
```bash
python scripts/validate.py
```
*Expected Output:*
```
Research pipeline validation audit:
Metadata checks:
[PASSED] country_metadata: 18 countries verified
[PASSED] product_catalog: 324 products, 24 targets across 7 sectors verified
Raw dataset audits:
[PASSED] wdi_raw_data: 450 rows across 18 countries (2000-2024)
[PASSED] comtrade_cache: 288 cached country-year batches verified
Algorithmic unit tests:
[PASSED] rca_calculation_and_safety
[PASSED] capability_classification
[PASSED] loco_proximity_properties
[PASSED] density_properties
[PASSED] lag_boundary_visibility
[PASSED] product_entry_rules
Empirical panel audits:
[PASSED] layer_a_empirical_panel: Rows: 93,312
[PASSED] layer_b_empirical_panel: Rows: 6,912
[PASSED] layer_a_gravity_panel: Rows: 93,312
Algorithmic Unit Tests Passed: True
```

### 2. Generate Data Quality Reports
To generate data profiling and missingness summaries across datasets:
```bash
python scripts/generate_data_quality_reports.py
```

### 3. Rebuild Panels from Cached Customs Records
To rebuild the Layer A grid, calculate LOCO proximity matrices, and assemble the discrete entry panel:
```bash
python scripts/prepare_data.py
python scripts/build_panel.py
python scripts/build_gravity_panel.py
```

---

## Known Limitations & Next Steps (at Week 4)

1. **Customs Data Caching:** Raw bilateral trade records comprise 288 JSON API batch files (~65 MB). To avoid API rate limiting and keep the repository lightweight, raw JSON caches and generated large panels (`data/processed/layer_a/`, `data/processed/layer_b/`) are excluded from Git tracking; scripts load from local caches or build them deterministically.
2. **Next Implementation Phase (Week 5 Onward):**
   - Econometric estimation of discrete choice entry models: Standard Logit (B1/B2), Two-Way Fixed Effects Logit (B3), Firth Penalized Logit (B4), and Conditional Logit (B5).
   - High-dimensional Poisson Pseudo-Maximum Likelihood (PPML) gravity models on continuous export values.
   - Robustness checks across alternative RCA thresholds (0.8, 1.0, 1.2), lag lengths (1, 2, 3 years), and wild cluster bootstrap inference ($G=18$).
   - Machine learning benchmark models (Random Forest, XGBoost) with Leave-One-Country-Out cross-validation and SHAP feature importance.
