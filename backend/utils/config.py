import os

# Konfigurasi folder
UPLOAD_FOLDER = 'backend/product_system/product_uploads'
CSV_OUTPUT_FOLDER = 'backend/product_system/csv_outputs'
JSON_OUTPUT_FOLDER = 'backend/product_system/json_outputs'

for folder in [UPLOAD_FOLDER, CSV_OUTPUT_FOLDER, JSON_OUTPUT_FOLDER]:
    os.makedirs(folder, exist_ok=True)

AREA_MAPPING = {
    "01": {"ad_org_id": 1000006, "area_name": "PST"},
    "02": {"ad_org_id": 1000007, "area_name": "TLB"},
    "03": {"ad_org_id": 1000005, "area_name": "KTB"},
    "04": {"ad_org_id": 1000059, "area_name": "PKL"}
}

UOM_MAPPING = {
    "CTN10/BAG": 1000020,
    "BAG": 1000009,
    "CTN": 1000001,
    "CTN1/BAG": 1000029,
    "CTN6/PCH": 1000020,
    "CTN12/PCH": 1000020,
    "CTN4/JRG": 1000020,
}

PRODUCT_ID_MAPPING = {
    "FORTUNE PALM OIL PLP @1LT": 1000656,
    "FORTUNE PALM OIL PCH @2LT": 1000655,
    "FORTUNE PALM OIL PCH @1LT": 1000650,
    "FORTUNE PALM OIL JRG @5LT": 1000659,
    "FORTUNE PALM OIL PCH @1.8LT": 1007116,
    "FORTUNE PALM OIL PCH @0.9LT": 1007115,
}

# Nilai default jika mapping tidak ditemukan
DEFAULT_UOM_ID = 1000000
DEFAULT_PRODUCT_ID = 0
