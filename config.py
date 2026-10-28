import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", Path(__file__).resolve().parent))
DATA_DIR = Path(os.environ.get("DATA_DIR", PROJECT_ROOT / "data"))
RESULTS_DIR = Path(os.environ.get("RESULTS_DIR", PROJECT_ROOT / "results"))
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
METADATA_DIR = DATA_DIR / "metadata"

# Temporal study window (Weeks 2-4 balanced panel)
STUDY_START = 2009
STUDY_END = 2024
STUDY_YEARS = list(range(STUDY_START, STUDY_END + 1))

# 18 Sovereign Economies (10 advanced, 8 emerging)
COUNTRIES = [
    "USA", "DEU", "JPN", "FRA", "GBR", "KOR", "SGP", "ISR", "NLD", "IRL",
    "CHN", "IND", "BRA", "MEX", "POL", "CZE", "TUR", "MYS"
]

COUNTRY_REPORTER_CODES = {
    "USA": 842, "DEU": 276, "JPN": 392, "FRA": 251, "GBR": 826, "KOR": 410,
    "SGP": 702, "ISR": 376, "NLD": 528, "IRL": 372, "CHN": 156, "IND": 699,
    "BRA": 76,  "MEX": 484, "POL": 616, "CZE": 203, "TUR": 792, "MYS": 458
}

# World Bank WDI Indicator Definitions
WDI_INDICATORS = {
    "rd_expenditure": "GB.XPD.RSDV.GD.ZS",
    "researchers_rd": "SP.POP.SCIE.RD.P6",
    "patent_resident": "IP.PAT.RESD",
    "patent_nonresident": "IP.PAT.NRES",
    "scientific_publications": "IP.JRN.ARTC.SC",
    "fixed_broadband": "IT.NET.BBND.P2",
    "internet_users": "IT.NET.USER.ZS",
    "tertiary_enrolment": "SE.TER.ENRR",
    "government_education": "SE.XPD.TOTL.GD.ZS",
    "fdi": "BX.KLT.DINV.WD.GD.ZS",
    "manufacturing_value_added": "NV.IND.MANF.ZS",
    "trade_openness": "NE.TRD.GNFS.ZS",
    "gdp_current_usd": "NY.GDP.MKTP.CD",
    "population_total": "SP.POP.TOTL",
    "merchandise_exports_total": "TX.VAL.MRCH.CD.WT",
    "hightech_exports": "TX.VAL.TECH.MF.ZS"
}
