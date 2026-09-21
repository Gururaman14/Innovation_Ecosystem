import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"

RAW_DIR = DATA_DIR / "raw"
WDI_RAW_DIR = RAW_DIR / "wdi"
OECD_RAW_DIR = RAW_DIR / "oecd"
WIPO_RAW_DIR = RAW_DIR / "wipo"
TAIWAN_RAW_DIR = RAW_DIR / "taiwan"
WITS_RAW_DIR = RAW_DIR / "wits"
EDUCATION_RAW_DIR = RAW_DIR / "education"

PROCESSED_DIR = DATA_DIR / "processed"
MASTER_DIR = PROCESSED_DIR / "master"
GAP_ANALYSIS_DIR = PROCESSED_DIR / "gap_analysis"
COVERAGE_DIR = PROCESSED_DIR / "coverage"

AUDIT_DIR = DATA_DIR / "audit"
AUDIT_18_DIR = AUDIT_DIR / "18_country"
COMTRADE_AUDIT_DIR = AUDIT_DIR / "comtrade"
SOURCES_AUDIT_DIR = AUDIT_DIR / "sources"

STUDY_START = 2000
STUDY_END = 2025
STUDY_YEARS = list(range(STUDY_START, STUDY_END + 1))

COUNTRIES = {
    "IND": "India",
    "CHN": "China",
    "KOR": "South Korea",
    "TWN": "Taiwan",
    "ISR": "Israel",
    "BRA": "Brazil",
}

COMTRADE_CODES = {
    "IND": 356,
    "CHN": 156,
    "KOR": 410,
    "TWN": 158,
    "ISR": 376,
    "BRA": 76,
}

INDICATORS = {
    "hightech_exports": "TX.VAL.TECH.MF.ZS",
    "rd_expenditure": "GB.XPD.RSDV.GD.ZS",
    "researchers_rd": "SP.POP.SCIE.RD.P6",
    "patent_resident": "IP.PAT.RESD",
    "patent_nonresident": "IP.PAT.NRES",
    "internet_users": "IT.NET.USER.ZS",
    "fixed_broadband": "IT.NET.BBND.P2",
    "tertiary_enrolment": "SE.TER.ENRR",
    "government_education": "SE.XPD.TOTL.GD.ZS",
    "fdi": "BX.KLT.DINV.WD.GD.ZS",
    "manufacturing_value_added": "NV.IND.MANF.ZS",
}

INDICATOR_LABELS = {
    "TX.VAL.TECH.MF.ZS": "High-tech exports (% manufactured exports)",
    "GB.XPD.RSDV.GD.ZS": "R&D expenditure (% GDP)",
    "SP.POP.SCIE.RD.P6": "Researchers in R&D (per million people)",
    "IP.PAT.RESD": "Patent applications, residents",
    "IP.PAT.NRES": "Patent applications, non-residents",
    "IT.NET.USER.ZS": "Internet users (% population)",
    "IT.NET.BBND.P2": "Fixed broadband subscriptions (per 100)",
    "SE.TER.ENRR": "Tertiary enrolment rate (% gross)",
    "SE.XPD.TOTL.GD.ZS": "Gov. expenditure on education (% GDP)",
    "BX.KLT.DINV.WD.GD.ZS": "FDI net inflows (% GDP)",
    "FS.AST.PRVT.GD.ZS": "Domestic credit to private sector (% GDP)",
    "NV.IND.MANF.ZS": "Manufacturing value added (% GDP)",
}
