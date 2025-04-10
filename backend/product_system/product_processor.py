import pdfplumber

def extract_product_data(pdf_path):
    all_data = {
        "text": "",
        "tables": [],
        "checkboxes": {}
    }
    
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            
            text = page.extract_text()
            if text:
                all_data["text"] += text + "\n"
            
            
            tables = page.extract_tables()
            if tables:
                all_data["tables"].extend(tables)
    
    
    all_data["main_data"] = parse_main_data(all_data["text"])
    
    all_data["checkboxes"] = parse_checkboxes(all_data["text"])
    
    return all_data

def parse_main_data(text):
    data = {}
    lines = text.split("\n")
    
    # Parsing data utama
    for line in lines:
        if "NOMOR:" in line:
            data["NOMOR"] = line.split("NOMOR:")[1].strip()
        if "REF DOC:" in line:
            data["REF DOC"] = line.split("REF DOC:")[1].strip()
        if "REF CP NO :" in line:
            data["REF CP NO"] = line.split("REF CP NO :")[1].strip()
        if "PERIODE CP:" in line:
            data["PERIODE CP"] = line.split("PERIODE CP:")[1].strip()
        if "PRODUCT CATEGORY :" in line:
            data["PRODUCT CATEGORY"] = line.split("PRODUCT CATEGORY :")[1].strip()
        if "BRAND :" in line:
            data["BRAND"] = line.split("BRAND :")[1].strip()
        if "CHANNEL :" in line:
            data["CHANNEL"] = line.split("CHANNEL :")[1].strip()
        if "REGION :" in line:
            data["REGION"] = line.split("REGION :")[1].strip()
        if "SUB REGION :" in line:
            data["SUB REGION"] = line.split("SUB REGION :")[1].strip()
        if "DISTRIBUTOR :" in line:
            data["DISTRIBUTOR"] = line.split("DISTRIBUTOR :")[1].strip()
        if "PROMO TYPE :" in line:
            data["PROMO TYPE"] = line.split("PROMO TYPE :")[1].strip()
        if "SUB PROMO TYPE :" in line:
            data["SUB PROMO TYPE"] = line.split("SUB PROMO TYPE :")[1].strip()
        if "MECHANISM:" in line:
            data["MECHANISM"] = line.split("MECHANISM:")[1].strip()
    
    # Parsing checkbox PERLU UJI COBA LAGI CHECKBOX HAHA1
    data["COST CATEGORY"] = {
        "INCLUDE TRADING TERM": "☑" if "☑ INCLUDE TRADING TERM" in text else "☐",
        "EXCLUDE TRADING TERM": "☑" if "☑ EXCLUDE TRADING TERM" in text else "☐",
        "OTB": "☑" if "☑ OTB" in text else "☐",
        "PF": "☑" if "☑ PF" in text else "☐"
    }
    data["TIPE CP"] = {
        "CLAIM": "☑" if "☑ CLAIM" in text else "☐",
        "ON INVOICE": "☑" if "☑ ON INVOICE" in text else "☐",
        "PURCHASE": "☑" if "☑ PURCHASE" in text else "☐"
    }
    data["TIPE CLAIM"] = {
        "PRINCIPAL": "☑" if "☑ PRINCIPAL" in text else "☐",
        "DISTRIBUTOR": "☑" if "☑ DISTRIBUTOR" in text else "☐"
    }
    data["CLAIM BASED"] = {
        "SELLING - IN": "☑" if "☑ SELLING - IN" in text else "☐",
        "SELLING - OUT": "☑" if "☑ SELLING - OUT" in text else "☐"
    }
    
    return data

def parse_checkboxes(text):
    checkboxes = {
        "cost_category": {
            "INCLUDE TRADING TERM": {"field": "Cost_Category", "status": "Tidak Dicentang"},
            "EXCLUDE TRADING TERM": {"field": "Cost_Category", "status": "Tidak Dicentang"},
            "OTB": {"field": "Cost_Category", "status": "Tidak Dicentang"},
            "PF": {"field": "Cost_Category", "status": "Tidak Dicentang"}
        },
        "type_cp": {
            "CLAIM": {"field": "Tipe_CP", "status": "Tidak Dicentang"},
            "ON INVOICE": {"field": "Tipe_CP", "status": "Tidak Dicentang"},
            "PURCHASE": {"field": "Tipe_CP", "status": "Tidak Dicentang"}
        },
        "type_claim": {
            "PRINCIPAL": {"field": "Claim_Based", "status": "Tidak Dicentang"},
            "DISTRIBUTOR": {"field": "Claim_Based", "status": "Tidak Dicentang"}
        },
        "claim_based": {
            "SELLING - IN": {"field": "Claim_Based", "status": "Tidak Dicentang"},
            "SELLING - OUT": {"field": "Claim_Based", "status": "Tidak Dicentang"}
        }
    }
    
    lines = text.split("\n")
    for line in lines:
        for category, options in checkboxes.items():
            for option, details in options.items():
                if option in line:
                    details["status"] = "Dicentang" if "☑" in line else "Tidak Dicentang"
    
    return checkboxes