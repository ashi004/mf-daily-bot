# --- MASTER ENHANCED CONFIGURATION ---
TICKERS = {
    "indices": {
        "^NSEI": "NIFTY 50", 
        "^BSESN": "SENSEX",
        "^CRSLDX": "NIFTY 500"
    },
    "sectors": {
        # --- Core Financials ---
        "^NSEBANK": "Bank", 
        "^CNXPSUBANK": "PSU Bank",    # Missing: State-run Banks
        "NIFTY_FIN_SERVICE.NS": "Finance", # Missing: NBFCs/Fintech
        
        # --- Consumption & Tech ---
        "^CNXIT": "IT", 
        "^CNXFMCG": "FMCG",
        "NIFTY_CONSR_DURBL.NS": "Durables", # Missing: Appliances/Lifestyle
        "^CNXAUTO": "Auto",
        "^CNXMEDIA": "Media",
        
        # --- Healthcare & Industrials ---
        "^CNXPHARMA": "Pharma", 
        "NIFTY_HEALTHCARE.NS": "Healthcare", # Often more stable than Pharma
        "^CNXMETAL": "Metal",
        "^CNXINFRA": "Infra",
        "^CNXREALTY": "Realty",
        
        # --- Energy & Resources ---
        "^CNXENERGY": "Energy",
        "NIFTY_OIL_AND_GAS.NS": "Oil & Gas" # Missing: Petroleum/Refining
    },
    "commodities": {
        "GC=F": "Gold", 
        "SI=F": "Silver"
    }
}