# Innovation Ecosystem: Empirical Analysis of National Innovation Systems

An empirical research pipeline for evaluating national innovation ecosystems across six key economies—**Brazil, China, India, Israel, South Korea, and Taiwan**—over the 2000–2025 study window.

The project integrates cross-country indicator data from international organizations and national statistical agencies to address reporting gaps (notably for Taiwan and historical R&D indicators), conduct data quality audits, and build harmonized panel datasets.

---

## Project Structure

```
Innovation_Ecosystem/
├── data/
│   ├── raw/                      # Unmodified source data
│   │   ├── wdi/                  # World Bank WDI extractions
│   │   ├── oecd/                 # OECD MSTI SDMX data & schemas
│   │   ├── wipo/                 # WIPO patent statistics & Excel tables
│   │   ├── taiwan/               # TIPO patent statistics & TWNIC reports
│   │   ├── wits/                 # WITS trade data & export HTML records
│   │   └── education/            # Education expenditure series
│   ├── processed/                # Integrated and harmonized datasets
│   │   ├── master/               # Harmonized sequential panel datasets
│   │   ├── gap_analysis/         # Missingness audits by country and variable
│   │   └── coverage/             # Temporal coverage matrices & common-year subsets
│   └── audit/                    # Source availability and comparability audits
│       ├── 18_country/           # Peer country comparison audits
│       ├── comtrade/             # UN Comtrade reporter-year availability
│       └── sources/              # Cross-source availability audits & logs
├── src/                          # Source code and analysis pipeline
│   ├── config.py                 # Centralized paths, indicator definitions & parameters
│   ├── audit/                    # Audit and validation scripts
│   │   ├── wdi_audit.py          # World Bank WDI availability audit
│   │   ├── coverage_check.py     # Variable-level coverage matrix generator
│   │   ├── comtrade_audit.py     # UN Comtrade API availability audit
│   │   ├── alternative_sources.py# Multi-source audit (OECD, UIS, WIPO, ITU, UNIDO)
│   │   ├── country_selection.py  # 18-country peer comparison audit
│   │   ├── master_source_coverage.py # Master country × year × source audit
│   │   └── final_source_audit.py # Baseline multi-source coverage audit
│   ├── extraction/               # Data acquisition routines
│   │   ├── extract_wdi.py        # World Bank WDI API extractor
│   │   ├── extract_oecd.py       # OECD SDMX API extractor
│   │   └── inspect_wipo.py       # WIPO workbook inspector
│   └── processing/               # Data harmonization and merging routines
│       ├── gap_analysis.py       # Panel missingness grid analysis
│       └── merge_oecd.py         # OECD MSTI integration with WDI baseline
├── .gitignore                    # Git ignore rules for Python & data artifacts
├── requirements.txt              # Python package dependencies
└── README.md                     # Project documentation
```

---

## Data Sources

| Domain | Primary Source | Secondary / Supplementary Source |
| :--- | :--- | :--- |
| **High-Tech Exports** | World Bank (WDI) | UN Comtrade, WITS |
| **R&D Expenditure & Personnel** | World Bank (WDI) | OECD MSTI, UNESCO UIS |
| **Patents (Resident / Non-Resident)** | World Bank (WDI) | WIPO Statistics Database, TIPO (Taiwan) |
| **Digital Infrastructure** | World Bank (WDI) | ITU DataHub, TWNIC (Taiwan) |
| **Education & Human Capital** | World Bank (WDI) | UNESCO Institute for Statistics (UIS) |
| **Macroeconomic Controls** | World Bank (WDI) | UNCTAD, UNIDO |

---

## Getting Started

### Prerequisites

Python 3.10+ is recommended. Install required packages:

```bash
pip install -r requirements.txt
```

### Running the Pipeline

1. **Run Availability Audits**:
   ```bash
   python src/audit/wdi_audit.py
   python src/audit/coverage_check.py
   python src/audit/comtrade_audit.py
   python src/audit/country_selection.py
   ```

2. **Extract Raw Data**:
   ```bash
   python src/extraction/extract_wdi.py
   python src/extraction/extract_oecd.py
   python src/extraction/inspect_wipo.py
   ```

3. **Process & Harmonize**:
   ```bash
   python src/processing/gap_analysis.py
   python src/processing/merge_oecd.py
   ```
