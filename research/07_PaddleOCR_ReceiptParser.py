import os
import re
import json
import time

from paddleocr import PaddleOCR


# ============================================================
# INITIALIZE PADDLEOCR
# ============================================================

print("=" * 70)
print("INITIALIZING PADDLEOCR RECEIPT PARSER")
print("=" * 70)

ocr = PaddleOCR(
    lang="en",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    enable_mkldnn=False,
)

print("Model berhasil dimuat.")


# ============================================================
# HELPER
# ============================================================

def clean_number(text):
    if text is None:
        return None

    text = str(text).strip()

    negative = "(" in text and ")" in text

    digits = re.sub(r"[^\d]", "", text)

    if not digits:
        return None

    value = int(digits)

    if negative:
        value = -value

    return value


def normalize_text(text):
    return re.sub(r"\s+", " ", str(text).strip())


def is_number_line(text):
    text = str(text).strip()

    pattern = r"^[\(\-]?\s*[\d.,]+\s*\)?$"

    return bool(re.match(pattern, text))


def extract_lines(result):

    lines = []

    for res in result:

        data = res.json

        if isinstance(data, str):
            data = json.loads(data)

        if "res" in data:
            data = data["res"]

        texts = data.get("rec_texts", [])

        for text in texts:

            text = normalize_text(text)

            if text:
                lines.append(text)

    return lines


# ============================================================
# MERCHANT
# ============================================================

def detect_merchant(lines):

    # Texas Chicken
    for i, line in enumerate(lines):

        if line.upper() == "TEXAS":

            if i + 1 < len(lines):

                if lines[i + 1].upper() == "CHICKEN":

                    return "Texas Chicken"

    # Griya Bintara
    for line in lines:

        if "GRIYA BINTARA" in line.upper():

            return "Griya Bintara"

    return ""


# ============================================================
# TEXAS CHICKEN ITEMS
# ============================================================

def extract_texas_items(lines):

    items = []

    for i, line in enumerate(lines):

        upper = line.upper()

        # Hanya anggap sebagai item jika:
        # 1. Ada COMBO
        # 2. Bukan footer
        # 3. Baris berikutnya adalah angka

        if "COMBO" in upper:

            if "PEMBELIAN" in upper:
                continue

            if i + 1 >= len(lines):
                continue

            if not is_number_line(lines[i + 1]):
                continue

            price = clean_number(lines[i + 1])

            if price is None:
                continue

            name = line.replace("*", "").strip()

            items.append({
                "name": name,
                "quantity": 1,
                "unit_price": price,
                "total_price": price
            })

    return items


# ============================================================
# GRIYA ITEMS
# ============================================================

def extract_griya_items(lines):

    items = []

    # --------------------------------------------------------
    # Cari berdasarkan NAMA ITEM
    # --------------------------------------------------------

    item_names = [
        "G-BENG MAXX 32G",
        "MINERALE 600 ML"
    ]

    for item_name in item_names:

        for i, line in enumerate(lines):

            if item_name.upper() in line.upper():

                quantity = None
                unit_price = None
                total_price = None

                # Cari sampai 3 angka sebelum nama item
                numbers_before = []

                j = i - 1

                while j >= 0 and len(numbers_before) < 3:

                    if is_number_line(lines[j]):

                        numbers_before.insert(
                            0,
                            clean_number(lines[j])
                        )

                    else:

                        # Berhenti ketika menemukan teks lain
                        if numbers_before:
                            break

                    j -= 1

                if len(numbers_before) >= 3:

                    quantity = numbers_before[-3]
                    unit_price = numbers_before[-2]
                    total_price = numbers_before[-1]

                items.append({
                    "name": item_name,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total_price": total_price
                })

                break

    return items


# ============================================================
# ITEMS
# ============================================================

def extract_items(lines, merchant):

    if merchant == "Texas Chicken":

        return extract_texas_items(lines)

    if merchant == "Griya Bintara":

        return extract_griya_items(lines)

    return []


# ============================================================
# TEXAS TOTALS
# ============================================================

def extract_texas_totals(lines):

    subtotal = None
    tax = None
    grand_total = None
    service = 0
    voucher = 0

    for i, line in enumerate(lines):

        upper = line.upper()

        # ----------------------------------------------------
        # SUBTOTAL
        # ----------------------------------------------------

        if upper == "SUBTOTAL":

            # Cari PB1 setelah subtotal
            for j in range(i + 1, min(i + 4, len(lines))):

                if lines[j].upper() == "PB1":

                    if j + 1 < len(lines):

                        if is_number_line(lines[j + 1]):

                            subtotal = clean_number(
                                lines[j + 1]
                            )

                    break

        # ----------------------------------------------------
        # TOTAL
        # ----------------------------------------------------

        if upper == "TOTAL":

            numbers = []

            for j in range(i + 1, min(i + 4, len(lines))):

                if is_number_line(lines[j]):

                    value = clean_number(lines[j])

                    if value is not None:

                        numbers.append(value)

            # Texas:
            #
            # Total
            # 17,455
            # 192,000
            #
            # 17,455 = PB1
            # 192,000 = grand total

            if len(numbers) >= 2:

                tax = numbers[0]

                grand_total = numbers[1]

            elif len(numbers) == 1:

                grand_total = numbers[0]

    return {
        "subtotal": subtotal,
        "tax": tax,
        "service": service,
        "voucher": voucher,
        "grand_total": grand_total
    }


# ============================================================
# GRIYA TOTALS
# ============================================================

def extract_griya_totals(lines):

    subtotal = None
    tax = None
    service = 0
    voucher = 0
    grand_total = None

    # --------------------------------------------------------
    # VOUCHER
    # --------------------------------------------------------

    for i, line in enumerate(lines):

        if "VOUCHER" in line.upper():

            if i + 1 < len(lines):

                value = clean_number(lines[i + 1])

                if value is not None:

                    voucher = abs(value)

    # --------------------------------------------------------
    # TOTAL BELANJA
    # --------------------------------------------------------

    for i, line in enumerate(lines):

        if "TOTAL BELANJA" in line.upper():

            # Angka biasanya di baris berikutnya
            if i + 1 < len(lines):

                if is_number_line(lines[i + 1]):

                    grand_total = clean_number(
                        lines[i + 1]
                    )

            # Fallback kalau angka berada
            # di baris yang sama
            if grand_total is None and ":" in line:

                value = line.split(":", 1)[1]

                grand_total = clean_number(value)

    # --------------------------------------------------------
    # PPN
    # --------------------------------------------------------

    for line in lines:

        if "PPN" in line.upper():

            match = re.search(
                r"PPN\s*[=:]?\s*([\d.,]+)",
                line.upper()
            )

            if match:

                tax = clean_number(
                    match.group(1)
                )

    return {
        "subtotal": subtotal,
        "tax": tax,
        "service": service,
        "voucher": voucher,
        "grand_total": grand_total
    }


# ============================================================
# TOTALS
# ============================================================

def extract_totals(lines, merchant):

    if merchant == "Texas Chicken":

        return extract_texas_totals(lines)

    if merchant == "Griya Bintara":

        return extract_griya_totals(lines)

    return {
        "subtotal": None,
        "tax": None,
        "service": 0,
        "voucher": 0,
        "grand_total": None
    }


# ============================================================
# PARSE RECEIPT
# ============================================================

def parse_receipt(image_path):

    start_time = time.time()

    result = ocr.predict(image_path)

    elapsed = time.time() - start_time

    lines = extract_lines(result)

    merchant = detect_merchant(lines)

    items = extract_items(
        lines,
        merchant
    )

    totals = extract_totals(
        lines,
        merchant
    )

    parsed = {
        "merchant": merchant,
        "items": items,
        "subtotal": totals["subtotal"],
        "tax": totals["tax"],
        "service": totals["service"],
        "voucher": totals["voucher"],
        "grand_total": totals["grand_total"]
    }

    return parsed, lines, elapsed


# ============================================================
# TEST
# ============================================================

def test_receipt(receipt_name, image_path):

    print("\n" + "=" * 70)
    print(receipt_name)
    print("=" * 70)

    print(f"Image: {image_path}")

    if not os.path.exists(image_path):

        print("FILE TIDAK DITEMUKAN")

        return

    parsed, lines, elapsed = parse_receipt(
        image_path
    )

    print("\nRAW OCR LINES")
    print("-" * 70)

    for i, line in enumerate(lines):

        print(f"{i:02d}: {line}")

    print("\nPARSED RESULT")
    print("-" * 70)

    print(
        json.dumps(
            parsed,
            indent=4,
            ensure_ascii=False
        )
    )

    print("\n" + "-" * 70)
    print(
        f"INFERENCE TIME: {elapsed:.2f} seconds"
    )
    print("-" * 70)


# ============================================================
# RECEIPTS
# ============================================================

receipt1 = os.path.join(
    "receipts",
    "receipt1.jpeg"
)

receipt2 = os.path.join(
    "receipts",
    "receipt2.jpeg"
)


# ============================================================
# RUN
# ============================================================

test_receipt(
    "RECEIPT 1 — TEXAS CHICKEN",
    receipt1
)

test_receipt(
    "RECEIPT 2 — GRIYA BINTARA",
    receipt2
)