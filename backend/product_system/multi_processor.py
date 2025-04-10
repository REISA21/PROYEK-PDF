import pdfplumber
import csv
from datetime import datetime
import re
import json
import os
from utils.config import AREA_MAPPING, UOM_MAPPING

class MultiDocumentProcessor:
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
            print(f"Error extracting PDF from {pdf_path}: {str(e)}")
            
        return "\n".join(all_text), all_tables

    def save_tables_to_csv(self, tables, csv_path):
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            for table in tables:
                for row in table:
                    writer.writerow(row)
                writer.writerow(["---"] * len(table[0]))

    def parse_text(self, text):
        lines = text.split('\n')
        for line in lines:
            line = line.strip()

            # Nomor extraction
            nomor_match = re.search(r"CP\d{2}[A-Za-z]{3,5}\d{2,3}-\d+", line, re.IGNORECASE)
            if nomor_match:
                nomor = nomor_match.group(0)
                nomor = nomor.replace("CP20DJFAJ001", "CP20DJFAJ01")
                self.data["nomor"] = nomor

            # Date extraction
            date_match = re.search(r"(\d{2}/\d{2}/\d{4})\s*[-–]\s*(\d{2}/\d{2}/\d{4})", line, re.IGNORECASE)
            if date_match:
                try:
                    start_date = datetime.strptime(date_match.group(1), "%d/%m/%Y")
                    end_date = datetime.strptime(date_match.group(2), "%d/%m/%Y")
                    self.data["valid_from"] = start_date.strftime("%Y%m%d")
                    self.data["valid_to"] = end_date.strftime("%Y%m%d")
                except Exception as e:
                    print(f"Error parsing dates: {str(e)}")

            # Brand extraction
            brand_match = re.search(r"(?:BRAND|PRODUCT\s*BRAND)\s*[:=\s-]+\s*([A-Za-z\s]+)", line, re.IGNORECASE)
            if brand_match:
                brand = brand_match.group(1).strip().upper()
                brand = re.split(r"\s*REF\s*CP\s*NO", brand, flags=re.IGNORECASE)[0].strip()
                if brand and "REF CP NO" not in brand:
                    self.data["brand"] = brand

            # Distributor extraction
            distributor_match = re.search(r"DISTRIBUTOR\s*[:=]?\s*([A-Z0-9-]+)\s*-\s*CV", line, re.IGNORECASE)
            if distributor_match:
                distributor_code = distributor_match.group(1)
                area_code = distributor_code[-2:] if len(distributor_code) >= 2 else None
                self.data["area_code"] = area_code
                if area_code in AREA_MAPPING:
                    self.data["area_name"] = AREA_MAPPING[area_code]["area_name"]
                    self.data["ad_org_id"] = AREA_MAPPING[area_code]["ad_org_id"]

            # Sub promo type extraction
            if re.search(r"SUB\s*PROMO\s*TYPE\s*[:=]?", line, re.IGNORECASE):
                match = re.search(r"SUB\s*PROMO\s*TYPE\s*[:=]?\s*\d{2}[A-Za-z]+\s*-\s*([A-Za-z\s]+)", line, re.IGNORECASE)
                if match:
                    self.data["sub_promo_type"] = match.group(1).strip().upper()

            # Vendor cashback extraction
            if re.search(r"INCLUDE\s*TRADING\s*TERM\s*☑", line, re.IGNORECASE):
                self.data["vendor_cashback"] = "Y"
            elif re.search(r"EXCLUDE\s*TRADING\s*TERM\s*☑", line, re.IGNORECASE):
                self.data["vendor_cashback"] = "N"

            # SKU extraction
            sku_match = re.search(
                r"(MILA FLOUR BAG @1KG|MILA TEPUNG(?: \d+KG)?|TEPUNG MILA|FORTUNE (?:PREMIUM RICE|PALM OIL )?(?:PLP|PCH|JRG) @\d+(\.\d+)?[KL]T)", 
                line, 
                re.IGNORECASE
            )
            if sku_match:
                sku = sku_match.group(0)
                found = False
                for sku_entry in self.data["sku_data"]:
                    if sku_entry["sku"] == sku:
                        found = True
                        break
                if not found:
                    self.data["sku_data"].append({
                        "sku": sku,
                        "qty_allocated": 0,
                        "uom": None,
                        "c_uom_id": None,
                        "strata_discounts": []
                    })
                self.data["sku"] = sku
                print(f"SKU found in text: {self.data['sku']}")

            # UOM extraction from text (sebagai fallback)
            if not self.data["uom"]:
                uom_match = re.search(r"\b(\d*\.?\d+)?\s*(KG|LT|PC|PCS)\b", line, re.IGNORECASE)
                if uom_match:
                    uom = uom_match.group(2).upper()
                    self.data["uom"] = uom
                    self.data["c_uom_id"] = UOM_MAPPING.get(uom, 1000000)
                    print(f"UOM found in text: {self.data['uom']} (c_uom_id: {self.data['c_uom_id']})")

        # Fallback: Jika brand masih tidak ditemukan
        if not self.data["brand"]:
            for line in lines:
                brand_match = re.search(r"\b(MILA|FORTUNE|SARI MURNI)\b", line, re.IGNORECASE)
                if brand_match and "REF CP NO" not in line.upper():
                    self.data["brand"] = brand_match.group(1).strip().upper()
                    break

    def parse_csv(self, csv_path):
        current_table = None
        headers = []
        subheaders = []
        table_rows = []
        last_sku = None
        last_uom = None
        
        with open(csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row and row[0] == "---":
                    if table_rows:
                        qty_header = None
                        min_qty_header = None
                        disc_header = None
                        share_disc_header = None
                        sku_header = None
                        uom_header = None
                        header_row = None
                        subheader_row = None
                        data_start_idx = 0
                        is_sales_commitment = False

                        print(f"Processing table: {table_rows}")
                        for idx, table_row in enumerate(table_rows):
                            table_row = [cell.strip().replace("\n", " ") if cell else "" for cell in table_row]
                            if any(re.search(r"SALES\s*COMITMENT", cell, re.IGNORECASE) for cell in table_row):
                                is_sales_commitment = True
                                header_row = table_rows[0]
                                subheader_row = table_rows[1] if len(table_rows) > 1 else None
                                data_start_idx = 2
                                break
                            for cell in table_row:
                                if re.search(r"(MIN\s*QTY\s*/\s*CTN|MIN\s*QTY|MINIMUM\s*QUANTITY)", cell, re.IGNORECASE):
                                    min_qty_header = cell
                                    header_row = table_row
                                    data_start_idx = idx + 1
                                    break
                            for cell in table_row:
                                if re.search(r"(DISC\s*%|DISCOUNT\s*%|DISCOUNT)", cell, re.IGNORECASE):
                                    disc_header = cell
                                    header_row = table_row
                                    data_start_idx = idx + 1
                                    break
                            for cell in table_row:
                                if re.search(r"(SHARE\s*DIST\s*%|SHARE\s*DISCOUNT\s*%|SHARE\s*%|SHARE)", cell, re.IGNORECASE):
                                    share_disc_header = cell
                                    header_row = table_row
                                    data_start_idx = idx + 1
                                    break
                            for cell in table_row:
                                if re.search(r"(QTY\s*IN\s*CTN|QUANTITY\s*IN\s*CTN|QTY/CTN|QUANTITY|QTY|TOTAL\s*QTY)", cell, re.IGNORECASE):
                                    qty_header = cell
                                    header_row = table_row
                                    data_start_idx = idx + 1
                                    break
                            for cell in table_row:
                                if re.search(r"(SKU|PRODUCT|ITEM|NAMA\s*PRODUK|PRODUCT\s*NAME|ITEM\s*DESCRIPTION)", cell, re.IGNORECASE):
                                    sku_header = cell
                                    header_row = table_row
                                    data_start_idx = idx + 1
                                    break
                            for cell in table_row:
                                if re.search(r"(UOM|UNIT|SATUAN|MEASURE)", cell, re.IGNORECASE):
                                    uom_header = cell
                                    header_row = table_row
                                    data_start_idx = idx + 1
                                    break
                            for cell in table_row:
                                if re.search(r"(NO|ID OUTLET|NAMA OUTLET)", cell, re.IGNORECASE):
                                    if "NO" in table_row and "ID OUTLET" in table_row:
                                        current_table = "OUTLET LIST"
                                        header_row = table_row
                                        data_start_idx = idx + 1
                                        break
                            if min_qty_header or qty_header or sku_header or uom_header or current_table:
                                break

                        if is_sales_commitment:
                            current_table = "SALES COMMITMENT"
                            headers = header_row if header_row else table_rows[0]
                            subheaders = subheader_row if subheader_row else []
                            print(f"Detected SALES COMMITMENT table with headers: {headers}")
                            print(f"Subheaders: {subheaders}")
                        elif min_qty_header or disc_header or share_disc_header:
                            current_table = "STRATA DISCOUNT TABLE"
                            headers = header_row if header_row else table_rows[0]
                            self.data["strata_discounts"] = []
                            print(f"Detected STRATA DISCOUNT TABLE with headers: {headers}")
                        elif qty_header or sku_header:
                            current_table = "SALES COMMITMENT"
                            headers = header_row if header_row else table_rows[0]
                            print(f"Detected SALES COMMITMENT table with headers: {headers}")
                        elif current_table == "OUTLET LIST":
                            headers = header_row
                            print(f"Detected OUTLET LIST table with headers: {headers}")
                        else:
                            current_table = None
                            # Fallback: Coba cari SKU, QTY, atau diskon di baris data (tanpa header yang jelas)
                            for row in table_rows:
                                for cell in row:
                                    cell = cell.strip() if cell else ""
                                    # Cari SKU
                                    sku_match = re.search(
                                        r"(MILA FLOUR BAG @1KG|MILA TEPUNG(?: \d+KG)?|TEPUNG MILA|FORTUNE (?:PREMIUM RICE|PALM OIL )?(?:PLP|PCH|JRG) @\d+(\.\d+)?[KL]T)", 
                                        cell, 
                                        re.IGNORECASE
                                    )
                                    if sku_match:
                                        sku = sku_match.group(0)
                                        found = False
                                        for sku_entry in self.data["sku_data"]:
                                            if sku_entry["sku"] == sku:
                                                found = True
                                                break
                                        if not found:
                                            self.data["sku_data"].append({
                                                "sku": sku,
                                                "qty_allocated": 0,
                                                "uom": None,
                                                "c_uom_id": None,
                                                "strata_discounts": []
                                            })
                                        if not self.data["sku"]:
                                            self.data["sku"] = sku
                                        print(f"SKU found in table (no header): {sku}")
                                    # Cari QTY
                                    qty_match = re.search(r"\b\d+\s*(?:CTN|KG|LT|PCS)?\b", cell, re.IGNORECASE)
                                    if qty_match:
                                        qty_str = qty_match.group(0).strip()
                                        try:
                                            qty = int(re.search(r"\d+", qty_str).group(0))
                                            if self.data["qty_allocated"] is None:
                                                self.data["qty_allocated"] = qty
                                            print(f"QTY found in table (no header): {qty}")
                                        except Exception as e:
                                            print(f"Error parsing QTY in table (no header): {str(e)}")
                                    # Cari diskon
                                    disc_match = re.search(r"\b\d+\.?\d*\s*%", cell, re.IGNORECASE)
                                    if disc_match:
                                        disc_str = disc_match.group(0).replace("%", "").strip()
                                        try:
                                            disc = float(disc_str)
                                            if self.data["sku_data"]:
                                                self.data["sku_data"][0]["strata_discounts"].append({
                                                    "breakfrom": 1,
                                                    "breakto": None,
                                                    "disc": disc,
                                                    "share_disc": 0
                                                })
                                            print(f"Discount found in table (no header): {disc}")
                                        except Exception as e:
                                            print(f"Error parsing discount in table (no header): {str(e)}")

                        if current_table:
                            for row in table_rows[data_start_idx:]:
                                if current_table == "SALES COMMITMENT" and subheaders:
                                    while len(subheaders) < len(row):
                                        subheaders.append("")
                                    row_data = dict(zip(subheaders, row))
                                    row_data["SKU"] = row[0] if row else ""
                                else:
                                    row_data = dict(zip(headers, row))

                                if current_table == "SALES COMMITMENT":
                                    qty_str = row_data.get(qty_header, "").strip() if qty_header else ""
                                    if not qty_str:
                                        for key, value in row_data.items():
                                            if re.search(r"(QTY\s*IN\s*CTN|QUANTITY\s*IN\s*CTN|QTY/CTN|QUANTITY|QTY|TOTAL\s*QTY)", key, re.IGNORECASE):
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
                                        print(f"Error parsing QTY: {str(e)}")
                                        qty = None

                                    sku = row_data.get(sku_header, "").replace("\n", " ").strip() if sku_header else ""
                                    if not sku:
                                        for key, value in row_data.items():
                                            if re.search(r"(SKU|PRODUCT|ITEM|NAMA\s*PRODUK|PRODUCT\s*NAME|ITEM\s*DESCRIPTION)", key, re.IGNORECASE):
                                                sku = value.replace("\n", " ").strip()
                                                break
                                    if sku:
                                        print(f"SKU found in SALES COMMITMENT table: {sku}")

                                    uom = row_data.get(uom_header, "").strip() if uom_header else ""
                                    if not uom:
                                        for key, value in row_data.items():
                                            if re.search(r"(UOM|UNIT|SATUAN|MEASURE)", key, re.IGNORECASE):
                                                uom = value.strip().upper()
                                                break
                                    if not uom:
                                        # Fallback: Cari UOM berdasarkan pola di baris
                                        for value in row_data.values():
                                            uom_match = re.search(r"\b(KG|LT|CTN|PCS)\b", value, re.IGNORECASE)
                                            if uom_match:
                                                uom = uom_match.group(0).upper()
                                                break
                                    if uom:
                                        print(f"UOM found in SALES COMMITMENT table: {uom}")

                                    if sku and qty is not None:
                                        found = False
                                        for sku_entry in self.data["sku_data"]:
                                            if sku_entry["sku"] == sku:
                                                sku_entry["qty_allocated"] = qty
                                                if uom:
                                                    sku_entry["uom"] = uom
                                                    sku_entry["c_uom_id"] = UOM_MAPPING.get(uom, 1000000)
                                                found = True
                                                break
                                        if not found:
                                            self.data["sku_data"].append({
                                                "sku": sku,
                                                "qty_allocated": qty,
                                                "uom": uom if uom else None,
                                                "c_uom_id": UOM_MAPPING.get(uom, 1000000) if uom else None,
                                                "strata_discounts": []
                                            })
                                        if self.data["qty_allocated"] is None:
                                            self.data["qty_allocated"] = qty
                                        if not self.data["sku"]:
                                            self.data["sku"] = sku
                                        if uom and not self.data["uom"]:
                                            self.data["uom"] = uom
                                            self.data["c_uom_id"] = UOM_MAPPING.get(uom, 1000000)

                                elif current_table == "STRATA DISCOUNT TABLE":
                                    min_qty_str = row_data.get(min_qty_header, "").replace("'", "").strip()
                                    
                                    try:
                                        if '/' in min_qty_str:
                                            min_qty = int(min_qty_str.split('/')[0].strip())
                                            max_qty = None
                                        elif '-' in min_qty_str:
                                            lower_str, upper_str = map(str.strip, min_qty_str.split('-'))
                                            min_qty = int(lower_str) if lower_str.replace(',', '').isdigit() else 0
                                            max_qty = int(upper_str) if upper_str.replace(',', '').isdigit() else 0
                                        else:
                                            min_qty = int(min_qty_str) if min_qty_str.replace(',', '').isdigit() else 0
                                            max_qty = None

                                        if min_qty > 0:
                                            disc_str = row_data.get(disc_header, "").replace(",", ".").strip() if disc_header else ""
                                            disc = float(disc_str) if disc_str else 0.0

                                            share_disc_str = row_data.get(share_disc_header, "").replace(",", ".").strip() if share_disc_header else ""
                                            share_disc = float(share_disc_str) if share_disc_str and share_disc_str != "-" else 0

                                            uom = row_data.get(uom_header, "").strip() if uom_header else ""
                                            if not uom:
                                                for key, value in row_data.items():
                                                    if re.search(r"(UOM|UNIT|SATUAN|MEASURE)", key, re.IGNORECASE):
                                                        uom = value.strip().upper()
                                                        break
                                            if not uom:
                                                # Fallback: Cari UOM berdasarkan pola di baris
                                                for value in row_data.values():
                                                    uom_match = re.search(r"\b(KG|LT|CTN|PCS)\b", value, re.IGNORECASE)
                                                    if uom_match:
                                                        uom = uom_match.group(0).upper()
                                                        break
                                            if uom:
                                                print(f"UOM found in STRATA DISCOUNT table: {uom}")

                                            sku = row_data.get(sku_header, "").replace("\n", " ").strip() if sku_header else ""
                                            if not sku:
                                                for key, value in row_data.items():
                                                    if re.search(r"(SKU|PRODUCT|ITEM|NAMA\s*PRODUK|PRODUCT\s*NAME|ITEM\s*DESCRIPTION)", key, re.IGNORECASE):
                                                        sku = value.replace("\n", " ").strip()
                                                        break
                                            if sku:
                                                print(f"SKU found in STRATA DISCOUNT table: {sku}")
                                                last_sku = sku
                                                last_uom = uom
                                            else:
                                                sku = last_sku if last_sku else self.data["sku"]
                                                uom = last_uom if last_uom else self.data["uom"]

                                            if uom and sku:
                                                found = False
                                                for sku_entry in self.data["sku_data"]:
                                                    if sku_entry["sku"] == sku:
                                                        sku_entry["uom"] = uom
                                                        sku_entry["c_uom_id"] = UOM_MAPPING.get(uom, 1000000)
                                                        sku_entry["strata_discounts"].append({
                                                            "breakfrom": min_qty,
                                                            "breakto": max_qty,
                                                            "disc": disc,
                                                            "share_disc": share_disc
                                                        })
                                                        found = True
                                                        break
                                                if not found:
                                                    self.data["sku_data"].append({
                                                        "sku": sku,
                                                        "uom": uom,
                                                        "c_uom_id": UOM_MAPPING.get(uom, 1000000),
                                                        "strata_discounts": [{
                                                            "breakfrom": min_qty,
                                                            "breakto": max_qty,
                                                            "disc": disc,
                                                            "share_disc": share_disc
                                                        }],
                                                        "qty_allocated": self.data["qty_allocated"] if self.data["qty_allocated"] is not None else 0
                                                    })
                                                if not self.data["sku"]:
                                                    self.data["sku"] = sku
                                                    self.data["uom"] = uom
                                                    self.data["c_uom_id"] = UOM_MAPPING.get(uom, 1000000)
                                                    self.data["strata_discounts"] = [{
                                                        "breakfrom": min_qty,
                                                        "breakto": max_qty,
                                                        "disc": disc,
                                                        "share_disc": share_disc
                                                    }]

                                    except (ValueError, TypeError) as e:
                                        print(f"Error parsing STRATA DISCOUNT TABLE: {str(e)}")
                                        continue

                                elif current_table == "OUTLET LIST":
                                    outlet_id = row_data.get("ID OUTLET", "").strip()
                                    outlet_name = row_data.get("NAMA OUTLET", "").strip()
                                    print(f"Processing OUTLET LIST row - ID: {outlet_id}, Name: {outlet_name}")
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
            print("Warning: QTY IN CTN tidak ditemukan di dokumen. Menggunakan nilai default.")
            self.data["qty_allocated"] = 1
        
        if not self.data["vendor_cashback"]:
            self.data["vendor_cashback"] = "Y"
        
        if not self.data["area_code"] or not self.data["area_name"] or not self.data["ad_org_id"]:
            raise ValueError("Area code atau informasi area tidak ditemukan di dokumen.")
        
        if not self.data["sku"]:
            # Fallback: Coba ekstrak SKU dari nama file
            filename = os.path.basename(self.current_pdf_path)
            sku_match = re.search(
                r"(MILA_FLOUR|TEPUNG_MILA|FRI|[A-Z\s]+(?:\s*@\s*\d+(?:\.\d+)?(?:KG|LT|CTN|PCS))?)", 
                filename, 
                re.IGNORECASE
            )
            if sku_match:
                sku = sku_match.group(0).replace("_", " ").strip()
                self.data["sku_data"].append({
                    "sku": sku,
                    "qty_allocated": self.data["qty_allocated"],
                    "uom": "KG",
                    "c_uom_id": 1000000,
                    "strata_discounts": []
                })
                self.data["sku"] = sku
                print(f"SKU extracted from filename: {sku}")
            else:
                raise ValueError("SKU tidak ditemukan di dokumen.")
        
        if not self.data["uom"] or not self.data["c_uom_id"]:
            print("Warning: UOM tidak ditemukan di dokumen. Menggunakan nilai default.")
            self.data["uom"] = "KG"
            self.data["c_uom_id"] = 1000000

        # Pastikan setiap SKU memiliki strata_discounts
        for sku_entry in self.data["sku_data"]:
            if not sku_entry["strata_discounts"]:
                print(f"Warning: Strata discounts tidak ditemukan untuk SKU {sku_entry['sku']}. Menggunakan nilai default.")
                sku_entry["strata_discounts"].append({
                    "breakfrom": 1,
                    "breakto": None,
                    "disc": 0.0,
                    "share_disc": 0.0
                })

    def process(self, pdf_path, csv_path):
        self.current_pdf_path = pdf_path  # Simpan pdf_path untuk digunakan di validate_data
        self.reset_data()
        
        print(f"Processing file: {pdf_path}")
        text, tables = self.extract_text_and_tables(pdf_path)
        if not text and not tables:
            raise ValueError("Dokumen kosong atau tidak dapat dibaca.")
        
        print(f"Extracted tables: {tables}")
        self.save_tables_to_csv(tables, csv_path)
        self.parse_text(text)
        self.parse_csv(csv_path)
        
        self.validate_data()
        
        # Tentukan selectiontype untuk single file
        if self.data["outlets"]:
            self.data["selection_type"] = "ISC"
        else:
            self.data["selection_type"] = "IA"
            
        return self.data

    def generate_json(self, list_customer):
        self.validate_data()

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
            "qtyallocated": self.data["qty_allocated"],
            "issotrx": "Y",
            "ispickup": "N",
            "fl_isallowmultiplediscount": "N",
            "isincludingsubordinate": "N",
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
            "list_break": []
        }

        # Bersihkan list_customer untuk menghapus field "isactive"
        cleaned_list_customer = []
        for customer in list_customer:
            cleaned_customer = customer.copy()
            cleaned_customer.pop("isactive", None)  # Hapus "isactive" jika ada
            cleaned_list_customer.append(cleaned_customer)

        json_data["list_customer"] = cleaned_list_customer

        break_name = f"{self.data['nomor']} {self.data['brand']} {self.data['sub_promo_type']} {self.data['area_name']}".strip()

        # Simpan semua list_break
        all_breaks = []

        for idx, sku_entry in enumerate(self.data["sku_data"]):
            # Tentukan seqno
            vendor_seqno = 10  # Vendor Cashback selalu seqno lebih kecil
            share_seqno = 20   # Share Discount selalu seqno lebih besar

            # Hitung nilai maksimum dari breakfrom untuk menentukan breakto secara dinamis
            max_breakfrom = max(
                (strata["breakfrom"] for strata in sku_entry["strata_discounts"]),
                default=sku_entry["qty_allocated"] if sku_entry["qty_allocated"] > 0 else 1
            )
            default_breakto = max_breakfrom if max_breakfrom > 0 else 1

            base_break = {
                "m_discountschema_id": 0,
                "m_discountschemabreak_id": 0,
                "ad_org_id": 0,
                "seqno": 0,
                "targetbreak": "EP",
                "discounttype": "PVD",
                "breaktype": "M",
                "calculationtype": "Q",
                "name": break_name,
                "requirementtype": "MS",
                "productselection": "IOP",
                "c_uom_id": sku_entry["c_uom_id"],
                "m_product_id": sku_entry["sku"],
                "m_product_category_id": None,
                "budgettype": "GB",
                "budgetcalculation": "QTY",
                "qtyallocated": sku_entry["qty_allocated"],
                "breakvalue": 0,
                "breakdiscount": 0,
                "isincludingsubordinate": "N",
                "isshareddiscount": "N",
                "isonlycountmaxrange": "Y",
                "istragetbeforediscount": "N",
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
            if "strata_discounts" in sku_entry:
                vendor_break = base_break.copy()
                vendor_break["seqno"] = vendor_seqno
                vendor_break["isshareddiscount"] = "N"
                vendor_break["isvendorcashback"] = "Y"
                vendor_break["list_line"] = []
                
                # Tambahkan semua entri dari strata_discounts
                sorted_strata = sorted(sku_entry["strata_discounts"], key=lambda x: x["breakfrom"])
                
                for i, strata in enumerate(sorted_strata):
                    if strata["breakto"]:
                        current_breakvalueto = strata["breakto"]
                    elif i < len(sorted_strata) - 1:
                        next_breakfrom = sorted_strata[i + 1]["breakfrom"]
                        current_breakvalueto = next_breakfrom - 1
                    else:
                        # Untuk entri terakhir, gunakan qtyallocated
                        current_breakvalueto = sku_entry["qty_allocated"]

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
                all_breaks.append(vendor_break)

            # Share Discount (SHARE DIST %)
            if "strata_discounts" in sku_entry:
                share_break = base_break.copy()
                share_break["seqno"] = share_seqno
                share_break["isshareddiscount"] = "Y"
                share_break["isvendorcashback"] = "N"
                share_break["list_line"] = []
                
                sorted_strata = sorted(sku_entry["strata_discounts"], key=lambda x: x["breakfrom"])
                
                # Untuk list_break terakhir per SKU (isshareddiscount: "Y"), hanya ambil satu entri
                # Pilih entri pertama dengan share_disc > 0, atau entri pertama jika semua share_disc = 0
                selected_strata = next((strata for strata in sorted_strata if strata["share_disc"] > 0), sorted_strata[0])
                
                # Aturan khusus untuk SKU @10KG dan share discount 0.5%
                if sku_entry["sku"].endswith("@10KG") and selected_strata["share_disc"] == 0.5:
                    current_breakvalue = selected_strata["breakfrom"]
                    current_breakvalueto = 4  # Aturan khusus: breakvalueto = 4
                else:
                    # Jika breakdiscount adalah 1%, paksa breakvalue 1 dan breakvalueto 99
                    if selected_strata["share_disc"] == 1:
                        current_breakvalue = 1
                        current_breakvalueto = 99
                    else:
                        current_breakvalue = selected_strata["breakfrom"]
                        if selected_strata["breakto"]:
                            current_breakvalueto = selected_strata["breakto"]
                        else:
                            # Tentukan breakvalueto secara dinamis berdasarkan sub_promo_type
                            if self.data["sub_promo_type"] == "STRATA DISCOUNT":
                                current_breakvalueto = default_breakto - 1 if default_breakto > 1 else 1
                            elif self.data["sub_promo_type"] == "DEAL KHUSUS":
                                current_breakvalueto = default_breakto - 1 if default_breakto > 1 else 1
                            else:
                                current_breakvalueto = default_breakto

                share_break["list_line"].append({
                    "m_discountschemabreak_id": 0,
                    "uns_dsbreakline_id": 0,
                    "name": break_name,
                    "breakvalue": current_breakvalue,
                    "breakvalueto": current_breakvalueto,
                    "qtyallocated": sku_entry["qty_allocated"],
                    "breakdiscount": selected_strata["share_disc"],
                    "seconddiscount": 0,
                    "thirddiscount": 0,
                    "fourthdiscount": 0,
                    "fifthdiscount": 0,
                    "isactive": "Y",
                    "list_bonus": [],
                    "list_budget": []
                })
                all_breaks.append(share_break)

        # Urutkan list_break hanya berdasarkan seqno, pertahankan urutan asli SKU
        json_data["list_break"] = sorted(all_breaks, key=lambda x: x["seqno"])
        return json_data
    
def process_multiple_files(files):
    processors = []
    temp_files = []
    errors = []

    try:
        # Proses setiap file
        for file in files:
            pdf_path = file["pdf_path"]
            csv_path = file["csv_path"]
            processor = MultiDocumentProcessor()
            try:
                data = processor.process(pdf_path, csv_path)
                processors.append({
                    "data": data,
                    "filename": file["filename"],
                    "processor": processor
                })
            except Exception as e:
                errors.append(f"Error processing {file['filename']}: {str(e)}")
            temp_files.append((pdf_path, csv_path))

        if errors:
            raise ValueError("\n".join(errors))

        # Validasi bahwa semua dokumen adalah untuk brand yang sama
        brands = [p["data"]["brand"] for p in processors]
        if len(set(brands)) != 1:
            raise ValueError("Semua dokumen harus untuk brand yang sama.")

        # Validasi bahwa semua dokumen memiliki nomor yang berbeda
        nomors = [p["data"]["nomor"] for p in processors]
        if len(set(nomors)) != len(nomors):
            raise ValueError("Semua dokumen harus memiliki nomor CP yang berbeda.")

        # Tentukan apakah ada dokumen yang memiliki daftar toko (outlets)
        has_outlets = any(p["data"]["outlets"] for p in processors)

        # Atur selectiontype untuk setiap dokumen berdasarkan aturan
        for p in processors:
            if p["data"]["outlets"]:
                p["data"]["selection_type"] = "ISC"  # Dokumen ini memiliki daftar toko
            else:
                if has_outlets:
                    p["data"]["selection_type"] = "ESC"  # Dokumen ini tidak memiliki daftar toko, tetapi ada dokumen lain yang memiliki
                else:
                    p["data"]["selection_type"] = "IA"  # Tidak ada dokumen yang memiliki daftar toko

        # Cari daftar outlet yang valid (tidak kosong) dari salah satu dokumen
        list_customer = []
        for p in processors:
            outlets = p["data"]["outlets"]
            if outlets:  # Jika daftar outlet tidak kosong
                list_customer = outlets
                break  # Ambil daftar outlet dari dokumen pertama yang memiliki outlets

        # Format list_customer untuk JSON
        list_customer_formatted = [
            {
                "m_discountschema_id": 0,
                "uns_discount_customer_id": 0,
                "m_discountschemabreak_id": 0,
                "ad_org_id": 0,
                "c_bpartner_id": outlet["c_bpartner_id"],
                "name": outlet["name"],
                "isactive": "Y"
            }
            for outlet in list_customer
        ]

        # Buat JSON untuk setiap dokumen dan kembalikan pasangan (json_data, nomor)
        json_outputs = []
        for p in processors:
            processor = p["processor"]
            nomor = p["data"]["nomor"]
            json_data = processor.generate_json(list_customer_formatted)
            json_outputs.append((json_data, nomor))

        return json_outputs

    finally:
        # Hapus file sementara
        for pdf_path, csv_path in temp_files:
            if os.path.exists(pdf_path):
                os.remove(pdf_path)
            if os.path.exists(csv_path):
                os.remove(csv_path)