import pdfplumber

def extract_all_data_from_pdf(file):
    all_data = {
        "text": "",
        "tables": []
    }
    
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            # Ekstrak teks
            text = page.extract_text()
            print("Extracted Text:", text)  # Debugging: Cetak teks yang diekstrak
            all_data["text"] += text
            
            # Ekstrak tabel
            tables = page.extract_tables()
            print("Extracted Tables:", tables)  # Debugging: Cetak tabel yang diekstrak
            all_data["tables"].extend(tables)
    
    return all_data

def parse_main_data(text):
    data = {}
    lines = text.split("\n")
    
    for line in lines:
        if "NOMOR:" in line:
            data["Nomor"] = line.split("NOMOR:")[1].strip()
        if "PRODUCT CATEGORY :" in line:
            parts = line.split("PRODUCT CATEGORY :")[1].split("REF DOC:")
            data["PRODUCT CATEGORY"] = parts[0].strip()
            data["REF DOC"] = parts[1].strip() if len(parts) > 1 else "KOSONG"
        if "BRAND :" in line:
            parts = line.split("BRAND :")[1].split("REF CP NO :")
            data["BRAND"] = parts[0].strip()
            data["REF CP NO"] = parts[1].strip() if len(parts) > 1 else "KOSONG"
        if "CHANNEL :" in line:
            parts = line.split("CHANNEL :")[1].split("PERIODE CP:")
            data["CHANNEL"] = parts[0].strip()
            data["PERIODE CP"] = parts[1].strip() if len(parts) > 1 else "KOSONG"
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
        if "COST CATEGORY" in line:
            data["COST CATEGORY"] = line.split("COST CATEGORY")[1].strip()
        if "TIPE CP" in line:
            data["TIPE CP"] = line.split("TIPE CP")[1].strip()
        if "CLAIM BASED" in line:
            data["CLAIM BASED"] = line.split("CLAIM BASED")[1].strip()
        if "MECHANISM:" in line:
            data["MECHANISM"] = line.split("MECHANISM:")[1].strip()
    
    return data

def parse_discount_promotion(table):
    parsed_data = []
    if not table or len(table) < 2:  # Skip tabel kosong atau tanpa data
        return parsed_data
    
    header = table[0]  # Baris pertama adalah header
    for row in table[1:]:  # Baris berikutnya adalah data
        if not any(row):  # Skip baris kosong
            continue
        
        row_data = {
            "SKU": row[header.index("SKU")] if "SKU" in header else "KOSONG",
            "UOM": row[header.index("UOM")] if "UOM" in header else "KOSONG",
            "PRICE LIST SATP": row[header.index("PRICE LIST SATP")] if "PRICE LIST SATP" in header else "KOSONG",
            "DISC %": {
                "REG": row[header.index("REG")] if "REG" in header else "KOSONG",
                "IOM": row[header.index("IOM")] if "IOM" in header else "KOSONG",
                "OTH": row[header.index("OTH")] if "OTH" in header else "KOSONG"
            },
            "RBP DIST": row[header.index("RBP DIST")] if "RBP DIST" in header else "KOSONG",
            "STRATA": row[header.index("STRATA")] if "STRATA" in header else "KOSONG",
            "Additional Disc %": {
                "D1": row[header.index("D1")] if "D1" in header else "KOSONG",
                "D2": row[header.index("D2")] if "D2" in header else "KOSONG",
                "D3": row[header.index("D3")] if "D3" in header else "KOSONG",
                "D4": row[header.index("D4")] if "D4" in header else "KOSONG",
                "D5": row[header.index("D5")] if "D5" in header else "KOSONG"
            },
            "CUT PRICE": {
                "OTB": row[header.index("OTB")] if "OTB" in header else "KOSONG",
                "PF": row[header.index("PF")] if "PF" in header else "KOSONG"
            },
            "RBP STORE": row[header.index("RBP STORE")] if "RBP STORE" in header else "KOSONG",
            "SHARE DIST %": row[header.index("SHARE DIST %")] if "SHARE DIST %" in header else "KOSONG",
            "RBP NET INC PPN": row[header.index("RBP NET INC PPN")] if "RBP NET INC PPN" in header else "KOSONG"
        }
        parsed_data.append(row_data)
    
    return parsed_data

def parse_strata_discount_table(table):
    parsed_data = []
    if not table or len(table) < 2:  # Skip tabel kosong atau tanpa data
        return parsed_data
    
    header = table[0]  # Baris pertama adalah header
    for row in table[1:]:  # Baris berikutnya adalah data
        if not any(row):  # Skip baris kosong
            continue
        
        row_data = {
            "SKU": row[header.index("SKU")] if "SKU" in header else "KOSONG",
            "UOM": row[header.index("UOM")] if "UOM" in header else "KOSONG",
            "MIN QTY / CTN": row[header.index("MIN QTY / CTN")] if "MIN QTY / CTN" in header else "KOSONG",
            "DISC %": row[header.index("DISC %")] if "DISC %" in header else "KOSONG",
            "RBP STORE OFF INV": row[header.index("RBP STORE OFF INV")] if "RBP STORE OFF INV" in header else "KOSONG",
            "CUT PRICE": {
                "OTB": row[header.index("OTB")] if "OTB" in header else "KOSONG",
                "PF": row[header.index("PF")] if "PF" in header else "KOSONG"
            },
            "SHARE DIST %": row[header.index("SHARE DIST %")] if "SHARE DIST %" in header else "KOSONG",
            "RBP NET INC PPN": row[header.index("RBP NET INC PPN")] if "RBP NET INC PPN" in header else "KOSONG"
        }
        parsed_data.append(row_data)
    
    return parsed_data

def parse_product_promotion(table):
    parsed_data = []
    if not table or len(table) < 2:  # Skip tabel kosong atau tanpa data
        return parsed_data
    
    header = table[0]  # Baris pertama adalah header
    for row in table[1:]:  # Baris berikutnya adalah data
        if not any(row):  # Skip baris kosong
            continue
        
        row_data = {
            "SKU": row[header.index("SKU")] if "SKU" in header else "KOSONG",
            "UOM": row[header.index("UOM")] if "UOM" in header else "KOSONG",
            "RBP DIST": row[header.index("RBP DIST")] if "RBP DIST" in header else "KOSONG",
            "MAX ITEM": row[header.index("MAX ITEM")] if "MAX ITEM" in header else "KOSONG",
            "STRATA": row[header.index("STRATA")] if "STRATA" in header else "KOSONG",
            "SKU BONUS": row[header.index("SKU BONUS")] if "SKU BONUS" in header else "KOSONG",
            "DESCRIPTION": row[header.index("DESCRIPTION")] if "DESCRIPTION" in header else "KOSONG",
            "Price (GBP/RBP/DBP/Cost)": row[header.index("Price (GBP/RBP/DBP/Cost)")] if "Price (GBP/RBP/DBP/Cost)" in header else "KOSONG",
            "QTY IN PCS": row[header.index("QTY IN PCS")] if "QTY IN PCS" in header else "KOSONG",
            "TOTAL BUDGET": row[header.index("TOTAL BUDGET")] if "TOTAL BUDGET" in header else "KOSONG"
        }
        parsed_data.append(row_data)
    
    return parsed_data

def parse_sales_commitment(table):
    parsed_data = []
    if not table or len(table) < 2:  # Skip tabel kosong atau tanpa data
        return parsed_data
    
    header = table[0]  # Baris pertama adalah header
    for row in table[1:]:  # Baris berikutnya adalah data
        if not any(row):  # Skip baris kosong
            continue
        
        row_data = {
            "SKU": row[header.index("SKU")] if "SKU" in header else "KOSONG",
            "QTY IN CTN": row[header.index("QTY IN CTN")] if "QTY IN CTN" in header else "KOSONG",
            "VALUE": row[header.index("VALUE")] if "VALUE" in header else "KOSONG",
            "TOTAL DISCOUNT": row[header.index("TOTAL DISCOUNT")] if "TOTAL DISCOUNT" in header else "KOSONG",
            "TOTAL PRODUCT PROMO": row[header.index("TOTAL PRODUCT PROMO")] if "TOTAL PRODUCT PROMO" in header else "KOSONG",
            "TOTAL OTB": row[header.index("TOTAL OTB")] if "TOTAL OTB" in header else "KOSONG",
            "TOTAL PF": row[header.index("TOTAL PF")] if "TOTAL PF" in header else "KOSONG",
            "TOTAL EST BUDGET PROMO": row[header.index("TOTAL EST BUDGET PROMO")] if "TOTAL EST BUDGET PROMO" in header else "KOSONG"
        }
        parsed_data.append(row_data)
    
    return parsed_data

def parse_tables(tables):
    parsed_tables = {
        "DISCOUNT PROMOTION": parse_discount_promotion(tables[0]) if len(tables) > 0 else [],
        "STRATA DISCOUNT TABLE": parse_strata_discount_table(tables[1]) if len(tables) > 1 else [],
        "PRODUCT PROMOTION": parse_product_promotion(tables[2]) if len(tables) > 2 else [],
        "SALES COMMITMENT": parse_sales_commitment(tables[3]) if len(tables) > 3 else []
    }
    return parsed_tables

def parse_checkboxes(text):
    checkboxes = {
        "cost_category": {
            "INCLUDE TRADING TERM": {"field": "Cost_Category", "default": "KOSONG"},
            "EXCLUDE TRADING TERM": {"field": "Cost_Category", "default": "KOSONG"},
            "OTB": {"field": "Cost_Category", "default": "KOSONG"},
            "PF": {"field": "Cost_Category", "default": "KOSONG"}
        },
        "type_cp": {
            "CLAIM": {"field": "Tipe_CP", "default": "KOSONG"},
            "ON INVOICE": {"field": "Tipe_CP", "default": "KOSONG"},
            "PURCHASE": {"field": "Tipe_CP", "default": "KOSONG"}
        },
        "type_claim": {
            "PRINCIPAL": {"field": "Claim_Based", "default": "KOSONG"},
            "DISTRIBUTOR": {"field": "Claim_Based", "default": "KOSONG"}
        },
        "claim_based": {
            "SELLING - IN": {"field": "Claim_Based", "default": "KOSONG"},
            "SELLING - OUT": {"field": "Claim_Based", "default": "KOSONG"}
        }
    }
    
    lines = text.split("\n")
    for line in lines:
        for category, options in checkboxes.items():
            for option, details in options.items():
                if option in line:
                    details["field"] = "Dicentang" if "✔" in line else "Tidak Dicentang"
    
    return checkboxes

# Contoh penggunaan
file_path = "CP20DJFAJ001-2400951 DK BERAS FORTUNE.pdf"
data = extract_all_data_from_pdf(file_path)
main_data = parse_main_data(data["text"])
tables_data = parse_tables(data["tables"])
checkboxes_data = parse_checkboxes(data["text"])

# Cetak hasil
print("Main Data:", main_data)
print("Tables Data:", tables_data)
print("Checkboxes Data:", checkboxes_data)