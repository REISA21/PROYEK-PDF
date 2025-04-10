import pdfplumber
import csv
from datetime import datetime
import re
import json
from utils.config import AREA_MAPPING, UOM_MAPPING

class DocumentProcessor:
    def __init__(self):
        self.reset_data()
        
    def reset_data(self):
        self.data = {
            "nomor": None,
            "brand": None,
            "sub_promo_type": None,
            "valid_from": None,
            "valid_to": None,
            "qty_allocated": None,
            "vendor_cashback": None,
            "area_code": None,
            "area_name": None,
            "ad_org_id": None,
            "sku": None,
            "uom": None,
            "c_uom_id": None,
            "outlets": [],
            "strata_discounts": [],
            "selection_type": None,
            "sku_data": []
        }
        print("Data reset:", self.data)

    def extract_text_and_tables(self, pdf_path):
        all_text = []
        all_tables = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        all_text.append(text)
                    
                    tables = page.extract_tables()
                    for table in tables:
                        if table and len(table) > 1:
                            all_tables.append(table)
        except Exception as e:
            print(f"Error extracting PDF: {str(e)}")
            
        return "\n".join(all_text), all_tables

    def save_tables_to_csv(self, tables, csv_path):
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            for table in tables:
                print(f"Extracted table: {table}")
                for row in table:
                    writer.writerow(row)
                writer.writerow(["---"] * len(table[0]))

    def parse_text(self, text):
        print(f"Extracted text:\n{text}\n")
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            print(f"Processing line: '{line}'")

            # Nomor extraction
            nomor_match = re.search(r"CP\d{2}[A-Za-z]{3,5}\d{2,3}-\d+", line, re.IGNORECASE)
            if nomor_match:
                nomor = nomor_match.group(0)
                nomor = nomor.replace("CP20DJFAJ001", "CP20DJFAJ01")
                self.data["nomor"] = nomor
                print(f"Extracted nomor: {self.data['nomor']}")

            # Date extraction
            date_match = re.search(r"(\d{2}/\d{2}/\d{4})\s*[-–]\s*(\d{2}/\d{2}/\d{4})", line, re.IGNORECASE)
            if date_match:
                try:
                    start_date = datetime.strptime(date_match.group(1), "%d/%m/%Y")
                    end_date = datetime.strptime(date_match.group(2), "%d/%m/%Y")
                    self.data["valid_from"] = start_date.strftime("%Y%m%d")
                    self.data["valid_to"] = end_date.strftime("%Y%m%d")
                    print(f"Extracted valid_from: {self.data['valid_from']}, valid_to: {self.data['valid_to']}")
                except Exception as e:
                    print(f"Error parsing dates: {str(e)}")

            # Brand extraction
            brand_match = re.search(r"(?:BRAND|PRODUCT\s*BRAND)\s*[:=\s-]+\s*([A-Za-z\s]+)", line, re.IGNORECASE)
            if brand_match:
                brand = brand_match.group(1).strip().upper()
                brand = re.split(r"\s*REF\s*CP\s*NO", brand, flags=re.IGNORECASE)[0].strip()
                if brand and "REF CP NO" not in brand:
                    self.data["brand"] = brand
                    print(f"Extracted brand: {self.data['brand']}")

            # Distributor extraction
            distributor_match = re.search(r"DISTRIBUTOR\s*[:=]?\s*([A-Z0-9-]+)\s*-\s*CV", line, re.IGNORECASE)
            if distributor_match:
                distributor_code = distributor_match.group(1)
                area_code = distributor_code[-2:] if len(distributor_code) >= 2 else None
                self.data["area_code"] = area_code
                if area_code in AREA_MAPPING:
                    self.data["area_name"] = AREA_MAPPING[area_code]["area_name"]
                    self.data["ad_org_id"] = AREA_MAPPING[area_code]["ad_org_id"]
                print(f"Extracted area_code: {self.data['area_code']}, area_name: {self.data['area_name']}, ad_org_id: {self.data['ad_org_id']}")

            # Sub promo type extraction
            if re.search(r"SUB\s*PROMO\s*TYPE\s*[:=]?", line, re.IGNORECASE):
                match = re.search(r"SUB\s*PROMO\s*TYPE\s*[:=]?\s*\d{2}[A-Za-z]+\s*-\s*([A-Za-z\s]+)", line, re.IGNORECASE)
                if match:
                    self.data["sub_promo_type"] = match.group(1).strip().upper()
                    print(f"Extracted sub_promo_type: {self.data['sub_promo_type']}")

            # Vendor cashback extraction
            if re.search(r"INCLUDE\s*TRADING\s*TERM\s*☑", line, re.IGNORECASE):
                self.data["vendor_cashback"] = "Y"
                print(f"Extracted vendor_cashback: {self.data['vendor_cashback']}")
            elif re.search(r"EXCLUDE\s*TRADING\s*TERM\s*☑", line, re.IGNORECASE):
                self.data["vendor_cashback"] = "N"
                print(f"Extracted vendor_cashback: {self.data['vendor_cashback']}")

            # Selection type extraction
            if re.search(r"list toko include \(selectiontype=ISC\)", line, re.IGNORECASE):
                self.data["selection_type"] = "ISC"
                print(f"Extracted selection_type: {self.data['selection_type']}")
            elif re.search(r"list customer exclude \(selectiontype=ESC\)", line, re.IGNORECASE):
                self.data["selection_type"] = "ESC"
                print(f"Extracted selection_type: {self.data['selection_type']}")

            # SKU extraction
            sku_match = re.search(r"(MILA FLOUR BAG @1KG|FORTUNE (?:PREMIUM RICE|PALM OIL )?(?:PLP|PCH|JRG) @\d+(\.\d+)?[KL]T)", line, re.IGNORECASE)
            if sku_match:
                self.data["sku"] = sku_match.group(0)
                print(f"Extracted sku: {self.data['sku']}")

        # Fallback: Jika brand masih tidak ditemukan
        if not self.data["brand"]:
            for line in lines:
                brand_match = re.search(r"\b(MILA|FORTUNE|SARI MURNI)\b", line, re.IGNORECASE)
                if brand_match and "REF CP NO" not in line.upper():
                    self.data["brand"] = brand_match.group(1).strip().upper()
                    print(f"Extracted brand from text fallback: {self.data['brand']}")
                    break
            if not self.data["brand"]:
                print("Warning: No brand detected in primary or fallback text search")
    
    def parse_csv(self, csv_path):
        current_table = None
        headers = []
        subheaders = []
        table_rows = []
        last_sku = None
        last_uom = None
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    if row and row[0] == "---":
                        if table_rows:
                            qty_header = None
                            min_qty_header = None
                            header_row = None
                            subheader_row = None
                            data_start_idx = 0
                            is_sales_commitment = False

                            for idx, table_row in enumerate(table_rows):
                                table_row = [cell.strip().replace("\n", " ") if cell else "" for cell in table_row]
                                if any(re.search(r"SALES\s*COMITMENT", cell, re.IGNORECASE) for cell in table_row):
                                    is_sales_commitment = True
                                    header_row = table_rows[0]
                                    subheader_row = table_rows[1] if len(table_rows) > 1 else None
                                    data_start_idx = 2
                                    break
                                for cell in table_row:
                                    if re.search(r"(QTY\s*IN\s*CTN|QUANTITY\s*IN\s*CTN|QTY/CTN)", cell, re.IGNORECASE):
                                        qty_header = cell
                                        header_row = table_row
                                        data_start_idx = idx + 1
                                        break
                                for cell in table_row:
                                    if re.search(r"(MIN\s*QTY\s*/\s*CTN|MIN\s*QTY)", cell, re.IGNORECASE):
                                        min_qty_header = cell
                                        header_row = table_row
                                        data_start_idx = idx + 1
                                        break
                                if qty_header or min_qty_header:
                                    break

                            if is_sales_commitment:
                                current_table = "SALES COMMITMENT"
                                headers = header_row if header_row else table_rows[0]
                                subheaders = subheader_row if subheader_row else []
                                print(f"Detected SALES COMMITMENT table with headers: {headers}")
                                print(f"Subheaders: {subheaders}")
                            elif qty_header:
                                current_table = "SALES COMMITMENT"
                                headers = header_row if header_row else table_rows[0]
                                print(f"Detected SALES COMMITMENT table with headers: {headers}")
                            elif min_qty_header:
                                current_table = "STRATA DISCOUNT TABLE"
                                headers = header_row if header_row else table_rows[0]
                                self.data["strata_discounts"] = []
                                print(f"Detected STRATA DISCOUNT TABLE with headers: {headers}")
                            elif any("DISCOUNT PROMOTION" in cell for cell in table_rows[0]) or any("PRICE LIST" in cell for cell in table_rows[0]):
                                current_table = "DISCOUNT PROMOTION"
                                headers = table_rows[0]
                                print(f"Detected DISCOUNT PROMOTION table with headers: {headers}")
                            elif any("MIX ITEM" in cell for cell in table_rows[0]):
                                current_table = "PRODUCT PROMOTION"
                                headers = table_rows[0]
                                print(f"Detected PRODUCT PROMOTION table with headers: {headers}")
                            elif "NO" in table_rows[0] and "ID OUTLET" in table_rows[0]:
                                current_table = "OUTLET LIST"
                                headers = table_rows[0]
                                print(f"Detected OUTLET LIST table with headers: {headers}")
                            else:
                                current_table = None
                                print(f"No relevant table detected in: {table_rows}")

                            if current_table:
                                for row in table_rows[data_start_idx:]:
                                    if current_table == "SALES COMMITMENT" and subheaders:
                                        while len(subheaders) < len(row):
                                            subheaders.append("")
                                        row_data = dict(zip(subheaders, row))
                                        row_data["SKU"] = row[0] if row else ""
                                    else:
                                        row_data = dict(zip(headers, row))
                                    print(f"Row data: {row_data}")

                                    if current_table == "SALES COMMITMENT":
                                        qty_str = row_data.get("QTY IN CTN", "").strip()
                                        if not qty_str:
                                            for key, value in row_data.items():
                                                if re.search(r"(QTY\s*IN\s*CTN|QUANTITY\s*IN\s*CTN|QTY/CTN)", key, re.IGNORECASE):
                                                    qty_str = value.strip()
                                                    break
                                        try:
                                            if qty_str:
                                                if '/' in qty_str:
                                                    num, denom = map(int, qty_str.split('/'))
                                                    qty = num if denom == 0 else num // denom
                                                else:
                                                    qty = int(qty_str.replace('.', '')) if qty_str.replace('.', '').isdigit() else None
                                            else:
                                                qty = None
                                        except Exception as e:
                                            print(f"Error parsing QTY IN CTN: {str(e)}")
                                            qty = None

                                        sku = row_data.get("SKU", "").replace("\n", " ").strip()
                                        print(f"Processing SKU: {sku}, QTY: {qty}")
                                        if sku and qty is not None:
                                            found = False
                                            for sku_entry in self.data["sku_data"]:
                                                if sku_entry["sku"] == sku:
                                                    sku_entry["qty_allocated"] = qty
                                                    found = True
                                                    print(f"Updated qty_allocated for SKU {sku}: {qty}")
                                                    break
                                            if not found:
                                                self.data["sku_data"].append({
                                                    "sku": sku,
                                                    "qty_allocated": qty,
                                                    "uom": None,
                                                    "c_uom_id": None,
                                                    "strata_discounts": []
                                                })
                                                print(f"Added new SKU {sku} with qty_allocated: {qty}")
                                            if self.data["qty_allocated"] is None:
                                                self.data["qty_allocated"] = qty
                                                print(f"Set main qty_allocated: {self.data['qty_allocated']}")
                                            if not self.data["brand"]:
                                                brand_match = re.match(r"([A-Z]+)(?:\s+(?:PREMIUM RICE|PALM OIL))?(?:\s+(?:PLP|PCH|JRG))?(?:\s*@)", sku, re.IGNORECASE)
                                                if brand_match:
                                                    self.data["brand"] = brand_match.group(1).strip().upper()
                                                    print(f"Fallback brand from SKU: {self.data['brand']}")

                                    elif current_table == "STRATA DISCOUNT TABLE":
                                        min_qty_str = row_data.get("MIN QTY / CTN", "").replace("'", "").strip()
                                        
                                        try:
                                            if '-' in min_qty_str:
                                                lower_str, upper_str = map(str.strip, min_qty_str.split('-'))
                                                if '/' in lower_str:
                                                    num, denom = map(int, lower_str.split('/'))
                                                    min_qty = num if denom == 0 else num // denom
                                                else:
                                                    min_qty = int(lower_str) if lower_str.replace(',', '').isdigit() else 0
                                                
                                                if '/' in upper_str:
                                                    num, denom = map(int, upper_str.split('/'))
                                                    max_qty = num if denom == 0 else num // denom
                                                else:
                                                    max_qty = int(upper_str) if upper_str.replace(',', '').isdigit() else 0
                                            else:
                                                if '/' in min_qty_str:
                                                    num, denom = map(int, min_qty_str.split('/'))
                                                    min_qty = num if denom == 0 else num // denom
                                                else:
                                                    min_qty = int(min_qty_str) if min_qty_str.replace(',', '').isdigit() else 0
                                                max_qty = None

                                            if min_qty > 0:
                                                disc_str = row_data.get("DISC %", "").replace(",", ".").strip()
                                                disc = float(disc_str) if disc_str else 0.0

                                                share_disc_str = row_data.get("SHARE DIST %", "").replace(",", ".").strip()
                                                try:
                                                    share_disc = float(share_disc_str) if share_disc_str and share_disc_str != "-" else 0
                                                except ValueError:
                                                    share_disc = 0

                                                uom = row_data.get("UOM", "").strip()
                                                sku = row_data.get("SKU", "").replace("\n", " ").strip()
                                                if sku:
                                                    last_sku = sku
                                                    last_uom = uom
                                                else:
                                                    sku = last_sku
                                                    uom = last_uom

                                                if uom and sku:
                                                    found = False
                                                    for sku_entry in self.data["sku_data"]:
                                                        if sku_entry["sku"] == sku:
                                                            sku_entry["uom"] = uom
                                                            sku_entry["c_uom_id"] = UOM_MAPPING.get(uom, 1000000)
                                                            sku_entry["strata_discounts"] = sku_entry.get("strata_discounts", [])
                                                            if disc > 0 or share_disc > 0:
                                                                sku_entry["strata_discounts"].append({
                                                                    "breakfrom": min_qty,
                                                                    "breakto": max_qty,
                                                                    "disc": disc,
                                                                    "share_disc": share_disc
                                                                })
                                                            found = True
                                                            break
                                                    if not found:
                                                        strata_discounts = []
                                                        if disc > 0 or share_disc > 0:
                                                            strata_discounts.append({
                                                                "breakfrom": min_qty,
                                                                "breakto": max_qty,
                                                                "disc": disc,
                                                                "share_disc": share_disc
                                                            })
                                                        self.data["sku_data"].append({
                                                            "sku": sku,
                                                            "uom": uom,
                                                            "c_uom_id": UOM_MAPPING.get(uom, 1000000),
                                                            "strata_discounts": strata_discounts,
                                                            "qty_allocated": 0
                                                        })
                                                    if not self.data["sku"]:
                                                        self.data["sku"] = sku
                                                        self.data["uom"] = uom
                                                        self.data["c_uom_id"] = UOM_MAPPING.get(uom, 1000000)
                                                        if disc > 0 or share_disc > 0:
                                                            self.data["strata_discounts"] = [{
                                                                "breakfrom": min_qty,
                                                                "breakto": max_qty,
                                                                "disc": disc,
                                                                "share_disc": share_disc
                                                            }]
                                                    print(f"Set UOM: {self.data['uom']}, c_uom_id: {self.data['c_uom_id']}")
                                                if not self.data["brand"] and sku:
                                                    brand_match = re.match(r"([A-Z]+)(?:\s+(?:PREMIUM RICE|PALM OIL))?(?:\s+(?:PLP|PCH|JRG))?(?:\s*@)", sku, re.IGNORECASE)
                                                    if brand_match:
                                                        self.data["brand"] = brand_match.group(1).strip().upper()
                                                        print(f"Fallback brand from SKU: {self.data['brand']}")

                                        except (ValueError, TypeError) as e:
                                            print(f"Error parsing STRATA DISCOUNT TABLE: {str(e)}")
                                            continue

                                    elif current_table == "DISCOUNT PROMOTION":
                                        uom = row_data.get("UOM", "").strip()
                                        sku = row_data.get("SKU", "").replace("\n", " ").strip()
                                        if uom and sku:
                                            found = False
                                            for sku_entry in self.data["sku_data"]:
                                                if sku_entry["sku"] == sku:
                                                    sku_entry["uom"] = uom
                                                    sku_entry["c_uom_id"] = UOM_MAPPING.get(uom, 1000000)
                                                    found = True
                                                    break
                                            if not found:
                                                self.data["sku_data"].append({
                                                    "sku": sku,
                                                    "uom": uom,
                                                    "c_uom_id": UOM_MAPPING.get(uom, 1000000),
                                                    "qty_allocated": 0,
                                                    "strata_discounts": []
                                                })
                                            if not self.data["uom"]:
                                                self.data["uom"] = uom
                                                self.data["c_uom_id"] = UOM_MAPPING.get(uom, 1000000)
                                                print(f"Set UOM: {self.data['uom']}, c_uom_id: {self.data['c_uom_id']}")
                                        if not self.data["brand"] and sku:
                                            brand_match = re.match(r"([A-Z]+)(?:\s+(?:PREMIUM RICE|PALM OIL))?(?:\s+(?:PLP|PCH|JRG))?(?:\s*@)", sku, re.IGNORECASE)
                                            if brand_match:
                                                self.data["brand"] = brand_match.group(1).strip().upper()
                                                print(f"Fallback brand from SKU: {self.data['brand']}")

                                    elif current_table == "OUTLET LIST":
                                        outlet_id = row_data.get("ID OUTLET", "").strip()
                                        outlet_name = row_data.get("NAMA OUTLET", "").strip()
                                        if outlet_id and outlet_name:
                                            self.data["outlets"].append({"c_bpartner_id": outlet_id, "name": outlet_name})

                        current_table = None
                        headers = []
                        subheaders = []
                        table_rows = []
                        last_sku = None
                        last_uom = None
                        continue

                    table_rows.append(row)

        except Exception as e:
            print(f"Error parsing CSV: {str(e)}")
            raise

    def validate_data(self):
        if not self.data["nomor"]:
            raise ValueError("Nomor CP tidak ditemukan di dokumen.")
        
        if not self.data["brand"]:
            raise ValueError("Brand tidak ditemukan di dokumen.")
        
        if not self.data["sub_promo_type"]:
            raise ValueError("Sub promo type tidak ditemukan di dokumen.")
        
        if not self.data["valid_from"] or not self.data["valid_to"]:
            raise ValueError("Periode valid_from atau valid_to tidak ditemukan di dokumen.")
        
        if self.data["qty_allocated"] is None:
            raise ValueError("QTY IN CTN tidak ditemukan di dokumen.")
        
        if not self.data["vendor_cashback"]:
            self.data["vendor_cashback"] = "Y"
        
        if not self.data["area_code"] or not self.data["area_name"] or not self.data["ad_org_id"]:
            raise ValueError("Area code atau informasi area tidak ditemukan di dokumen.")
        
        if not self.data["sku"]:
            raise ValueError("SKU tidak ditemukan di dokumen.")
        
        if not self.data["uom"] or not self.data["c_uom_id"]:
            raise ValueError("UOM tidak ditemukan di dokumen.")
        
        if not self.data["strata_discounts"]:
            self.data["strata_discounts"] = []  # Allow empty strata_discounts
        
        if not self.data["selection_type"]:
            self.data["selection_type"] = "IA"

        for sku_entry in self.data["sku_data"]:
            if "uom" not in sku_entry or not sku_entry["uom"]:
                raise ValueError(f"UOM tidak ditemukan untuk SKU: {sku_entry['sku']}")
            if "c_uom_id" not in sku_entry or not sku_entry["c_uom_id"]:
                raise ValueError(f"c_uom_id tidak ditemukan untuk SKU: {sku_entry['sku']}")
            if "qty_allocated" not in sku_entry or sku_entry["qty_allocated"] is None:
                raise ValueError(f"qty_allocated tidak ditemukan untuk SKU: {sku_entry['sku']}")
            if "strata_discounts" not in sku_entry:
                sku_entry["strata_discounts"] = []  # Allow empty strata_discounts

    def generate_json(self):
        try:
            self.validate_data()

            print(f"Before generating JSON - brand: {self.data['brand']}, area_name: {self.data['area_name']}, sub_promo_type: {self.data['sub_promo_type']}")

            name_description = f"{self.data['brand']} {self.data['sub_promo_type']} {self.data['area_name']}".strip()

            json_data = {
                "m_discountschema_id": 0,
                "ad_org_id": 0,
                "c_doctype_id": 1000134,
                "name": name_description,
                "description": name_description,
                "discounttype": "B",
                "vendor_id": 1000078,
                "requirementtype": "MS",
                "flatdiscounttype": "P",
                "cumulativelevel": "L",
                "validfrom": self.data["valid_from"],
                "validto": self.data["valid_to"],
                "selectiontype": self.data["selection_type"],
                "budgettype": "NB",
                "organizationaleffectiveness": "ISO",
                "qtyallocated": 0,
                "issotrx": "Y",
                "ispickup": "N",
                "fl_isallowmultiplediscount": "N",
                "isincludingsubordinate": "N",
                "iscashpayment": "N",
                "isbirthdaydiscount": "N",
                "isactive": "Y",
                "list_org": [
                    {
                        "m_discountschema_id": 0,
                        "uns_discount_org_id": 0,
                        "ad_org_id": 0,
                        "ad_orgtrx_id": self.data["ad_org_id"],
                        "isactive": "Y"
                    }
                ],
                "list_customer": [],
                "list_budget": [],
                "list_bonus": [],
                "list_break": []
            }

            print(f"Generated name_description: {name_description}")

            break_name = f"{self.data['nomor']} {self.data['brand']} {self.data['sub_promo_type']} {self.data['area_name']}".strip()

            for idx, sku_entry in enumerate(self.data["sku_data"]):
                if "1LT" in sku_entry["sku"] or "0.8LT" in sku_entry["sku"]:
                    vendor_seqno = 10
                    share_seqno = 20
                elif "2LT" in sku_entry["sku"] or "1.8LT" in sku_entry["sku"]:
                    vendor_seqno = 30
                    share_seqno = 40
                else:
                    vendor_seqno = 50
                    share_seqno = 60

                # Default breakvalueto adalah qtyallocated
                breakvalueto = sku_entry["qty_allocated"]

                base_break = {
                    "m_discountschema_id": 0,
                    "m_discountschemabreak_id": 0,
                    "ad_org_id": 0,
                    "seqno": 0,
                    "targetbreak": "EP",
                    "targetperiodic": None,
                    "discounttype": "PVD",
                    "breaktype": "M",
                    "calculationtype": "Q",
                    "selectiontype": None,
                    "name": break_name,
                    "requirementtype": "MS",
                    "productselection": "IOP",
                    "salestype": None,
                    "saleslevel": None,
                    "c_uom_id": sku_entry["c_uom_id"],
                    "m_product_id": sku_entry["sku"],
                    "m_product_category_id": None,
                    "vendor_id": None,
                    "budgettype": "GB",
                    "budgetcalculation": "QTY",
                    "qtyallocated": sku_entry["qty_allocated"],
                    "breakvalue": 0,
                    "breakdiscount": 0,
                    "isincludingsubordinate": "N",
                    "isshareddiscount": "N",
                    "isonlycountmaxrange": "Y",
                    "istragetbeforediscount": "N",  # Ditambahkan
                    "isbirthdaydiscount": "N",
                    "ismix": "N",
                    "isdiscountedbonus": "N",
                    "isstrictstrata": "Y",
                    "isvendorcashback": "N",
                    "ismixrequired": "N",
                    "isstratabudget": "Y",
                    "isactive": "Y",
                    "list_product": [],
                    "list_customer": [],
                    "list_bonus": [],
                    "list_budget": [],
                    "list_line": []
                }

                # Vendor Cashback (DISC %)
                if any(strata["disc"] > 0 for strata in sku_entry["strata_discounts"]):
                    vendor_break = base_break.copy()
                    vendor_break["seqno"] = vendor_seqno
                    vendor_break["isshareddiscount"] = "N"
                    vendor_break["isvendorcashback"] = "Y"
                    vendor_break["list_line"] = []
                    
                    # Urutkan strata_discounts berdasarkan breakfrom
                    sorted_strata = sorted(sku_entry["strata_discounts"], key=lambda x: x["breakfrom"])
                    
                    for i, strata in enumerate(sorted_strata):
                        if strata["disc"] > 0:
                            # Tentukan breakvalueto
                            if i < len(sorted_strata) - 1:
                                # Jika bukan strata terakhir, breakvalueto adalah breakfrom strata berikutnya - 1
                                next_breakfrom = sorted_strata[i + 1]["breakfrom"]
                                current_breakvalueto = next_breakfrom - 1
                            else:
                                # Jika strata terakhir, gunakan qtyallocated
                                current_breakvalueto = breakvalueto

                            vendor_break["list_line"].append({
                                "m_discountschemabreak_id": 0,
                                "uns_dsbreakline_id": 0,
                                "name": break_name,
                                "breakvalue": strata["breakfrom"],
                                "breakvalueto": current_breakvalueto,
                                "qtyallocated": sku_entry["qty_allocated"],
                                "breakdiscount": strata["disc"],
                                "seconddiscount": 0,
                                "thirddiscount": 0,
                                "fourthdiscount": 0,
                                "fifthdiscount": 0,
                                "isactive": "Y",
                                "list_bonus": [],
                                "list_budget": []
                            })
                    json_data["list_break"].append(vendor_break)

                # Share Discount (SHARE DIST %)
                if any(strata["share_disc"] > 0 for strata in sku_entry["strata_discounts"]):
                    share_break = base_break.copy()
                    share_break["seqno"] = share_seqno
                    share_break["isshareddiscount"] = "Y"
                    share_break["isvendorcashback"] = "N"
                    share_break["list_line"] = []
                    
                    # Urutkan strata_discounts berdasarkan breakfrom
                    sorted_strata = sorted(sku_entry["strata_discounts"], key=lambda x: x["breakfrom"])
                    
                    # Cari rentang pertama yang memiliki share_disc > 0
                    share_disc_range = None
                    for strata in sorted_strata:
                        if strata["share_disc"] > 0:
                            share_disc_range = strata
                            break
                    
                    if share_disc_range:
                        # Untuk Share Discount, breakvalueto selalu qtyallocated
                        share_breakfrom = share_disc_range["breakfrom"]
                        share_breakvalueto = breakvalueto

                        share_break["list_line"].append({
                            "m_discountschemabreak_id": 0,
                            "uns_dsbreakline_id": 0,
                            "name": break_name,
                            "breakvalue": share_breakfrom,
                            "breakvalueto": share_breakvalueto,
                            "qtyallocated": sku_entry["qty_allocated"],
                            "breakdiscount": share_disc_range["share_disc"],
                            "seconddiscount": 0,
                            "thirddiscount": 0,
                            "fourthdiscount": 0,
                            "fifthdiscount": 0,
                            "isactive": "Y",
                            "list_bonus": [],
                            "list_budget": []
                        })
                    json_data["list_break"].append(share_break)

            json_data["list_break"].sort(key=lambda x: x["seqno"])

            return json_data
            
        except Exception as e:
            print(f"Error generating JSON: {str(e)}")
            raise

    def process(self, pdf_path, csv_path):
        self.reset_data()
        
        try:
            text, tables = self.extract_text_and_tables(pdf_path)
            if not text and not tables:
                raise ValueError("Dokumen kosong atau tidak dapat dibaca.")
            
            self.save_tables_to_csv(tables, csv_path)
            self.parse_text(text)
            self.parse_csv(csv_path)
            
            json_data = self.generate_json()
            return json_data
        except Exception as e:
            print(f"Processing error: {str(e)}")
            raise

