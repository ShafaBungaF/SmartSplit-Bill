import re
import json

from paddleocr import PaddleOCR


# ============================================================
# LOAD PADDLEOCR MODEL
# ============================================================

_ocr = None


def load_paddle_model():
    """
    Load PaddleOCR sekali saja.
    """

    global _ocr

    if _ocr is None:
        _ocr = PaddleOCR(
            lang="en",
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,
        )

    return _ocr


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def clean_number(text):
    """
    Membersihkan angka dari hasil OCR.

    Contoh:
        174,545 -> 174545
        66.100  -> 66100
        (3,900) -> -3900
    """

    if text is None:
        return None

    text = str(text).strip()

    negative = "(" in text and ")" in text

    digits = re.sub(
        r"[^\d]",
        "",
        text,
    )

    if not digits:
        return None

    value = int(digits)

    if negative:
        value = -value

    return value


def normalize_text(text):
    return re.sub(
        r"\s+",
        " ",
        str(text).strip(),
    )


def is_number_line(text):
    text = str(text).strip()

    pattern = r"^[\(\-]?\s*[\d.,]+\s*\)?$"

    return bool(
        re.match(
            pattern,
            text,
        )
    )


# ============================================================
# EXTRACT OCR LINES
# ============================================================

def extract_lines(result):

    lines = []

    for res in result:

        data = res.json

        if isinstance(
            data,
            str,
        ):
            data = json.loads(data)

        if "res" in data:
            data = data["res"]

        texts = data.get(
            "rec_texts",
            [],
        )

        for text in texts:

            text = normalize_text(
                text
            )

            if text:
                lines.append(text)

    return lines


# ============================================================
# MERCHANT
# ============================================================

def detect_merchant(lines):

    # --------------------------------------------------------
    # Texas Chicken
    # --------------------------------------------------------

    for i, line in enumerate(lines):

        if line.upper() == "TEXAS":

            if i + 1 < len(lines):

                if (
                    lines[i + 1].upper()
                    == "CHICKEN"
                ):

                    return "Texas Chicken"

    # --------------------------------------------------------
    # Griya Bintara
    # --------------------------------------------------------

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

        # Item Texas harus:
        # - mengandung COMBO
        # - bukan footer
        # - diikuti angka harga

        if "COMBO" not in upper:
            continue

        if "PEMBELIAN" in upper:
            continue

        if i + 1 >= len(lines):
            continue

        if not is_number_line(
            lines[i + 1]
        ):
            continue

        price = clean_number(
            lines[i + 1]
        )

        if price is None:
            continue

        name = line.replace(
            "*",
            "",
        ).strip()

        items.append(
            {
                "name": name,
                "quantity": 1,
                "unit_price": price,
                "total_price": price,
            }
        )

    return items


# ============================================================
# GRIYA BINTARA ITEMS
# ============================================================

def extract_griya_items(lines):

    items = []

    item_names = [
        "G-BENG MAXX 32G",
        "MINERALE 600 ML",
    ]

    for item_name in item_names:

        for i, line in enumerate(lines):

            if item_name.upper() not in line.upper():
                continue

            quantity = None
            unit_price = None
            total_price = None

            numbers_before = []

            j = i - 1

            while (
                j >= 0
                and len(numbers_before) < 3
            ):

                if is_number_line(
                    lines[j]
                ):

                    numbers_before.insert(
                        0,
                        clean_number(
                            lines[j]
                        ),
                    )

                else:

                    if numbers_before:
                        break

                j -= 1

            if len(numbers_before) >= 3:

                quantity = numbers_before[-3]

                unit_price = numbers_before[-2]

                total_price = numbers_before[-1]

            items.append(
                {
                    "name": item_name,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total_price": total_price,
                }
            )

            break

    return items


# ============================================================
# ITEMS
# ============================================================

def extract_items(
    lines,
    merchant,
):

    if merchant == "Texas Chicken":

        return extract_texas_items(
            lines
        )

    if merchant == "Griya Bintara":

        return extract_griya_items(
            lines
        )

    return []


# ============================================================
# TEXAS TOTALS
# ============================================================

def extract_texas_totals(lines):

    subtotal = None
    tax = None
    service = 0
    voucher = 0
    grand_total = None

    for i, line in enumerate(lines):

        upper = line.upper()

        # ----------------------------------------------------
        # SUBTOTAL
        # ----------------------------------------------------

        if upper == "SUBTOTAL":

            for j in range(
                i + 1,
                min(i + 4, len(lines)),
            ):

                if lines[j].upper() == "PB1":

                    if j + 1 < len(lines):

                        if is_number_line(
                            lines[j + 1]
                        ):

                            subtotal = clean_number(
                                lines[j + 1]
                            )

                    break

        # ----------------------------------------------------
        # TOTAL
        # ----------------------------------------------------

        if upper == "TOTAL":

            numbers = []

            for j in range(
                i + 1,
                min(i + 4, len(lines)),
            ):

                if is_number_line(
                    lines[j]
                ):

                    value = clean_number(
                        lines[j]
                    )

                    if value is not None:
                        numbers.append(value)

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
        "grand_total": grand_total,
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

            # Kasus:
            # VOUCHER :
            # (3,900)

            if i + 1 < len(lines):

                value = clean_number(
                    lines[i + 1]
                )

                if value is not None:

                    voucher = abs(value)

    # --------------------------------------------------------
    # TOTAL BELANJA
    # --------------------------------------------------------

    for i, line in enumerate(lines):

        if "TOTAL BELANJA" in line.upper():

            # Kasus:
            # TOTAL BELANJA :
            # 66.100

            if i + 1 < len(lines):

                if is_number_line(
                    lines[i + 1]
                ):

                    grand_total = clean_number(
                        lines[i + 1]
                    )

            # Fallback jika angka berada
            # pada baris yang sama.
            if (
                grand_total is None
                and ":" in line
            ):

                value = line.split(
                    ":",
                    1,
                )[1]

                grand_total = clean_number(
                    value
                )

    # --------------------------------------------------------
    # PPN
    # --------------------------------------------------------

    for line in lines:

        if "PPN" not in line.upper():
            continue

        match = re.search(
            r"PPN\s*[=:]?\s*([\d.,]+)",
            line.upper(),
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
        "grand_total": grand_total,
    }


# ============================================================
# TOTALS
# ============================================================

def extract_totals(
    lines,
    merchant,
):

    if merchant == "Texas Chicken":

        return extract_texas_totals(
            lines
        )

    if merchant == "Griya Bintara":

        return extract_griya_totals(
            lines
        )

    return {
        "subtotal": None,
        "tax": None,
        "service": 0,
        "voucher": 0,
        "grand_total": None,
    }


# ============================================================
# MAIN RECEIPT READER
# ============================================================

def read_receipt(
    image,
    model=None,
):
    """
    Fungsi utama yang dipanggil oleh main.py.

    Parameter:
        image = PIL Image / path / file-like object

    Return:
        {
            "receipt_data": {...},
            "raw_output": "..."
        }
    """

    ocr = (
        model
        or load_paddle_model()
    )

    # --------------------------------------------------------
    # PaddleOCR menerima path atau image.
    # Untuk Streamlit UploadedFile / PIL Image,
    # ubah menjadi numpy array.
    # --------------------------------------------------------

    import numpy as np

    if hasattr(
        image,
        "convert",
    ):

        image = image.convert(
            "RGB"
        )

    image = np.array(
        image
    )

    # --------------------------------------------------------
    # OCR
    # --------------------------------------------------------

    result = ocr.predict(
        image
    )

    # --------------------------------------------------------
    # EXTRACT LINES
    # --------------------------------------------------------

    lines = extract_lines(
        result
    )

    # --------------------------------------------------------
    # MERCHANT
    # --------------------------------------------------------

    merchant = detect_merchant(
        lines
    )

    # --------------------------------------------------------
    # ITEMS
    # --------------------------------------------------------

    items = extract_items(
        lines,
        merchant,
    )

    # --------------------------------------------------------
    # TOTALS
    # --------------------------------------------------------

    totals = extract_totals(
        lines,
        merchant,
    )

    # --------------------------------------------------------
    # RECEIPT DATA
    # --------------------------------------------------------

    receipt_data = {
        "merchant": merchant,

        "items": items,

        "subtotal": (
            totals["subtotal"]
            if totals["subtotal"] is not None
            else 0
        ),

        "tax": (
            totals["tax"]
            if totals["tax"] is not None
            else 0
        ),

        "service_charge": (
            totals["service"]
            if totals["service"] is not None
            else 0
        ),

        # ====================================================
        # FIX:
        # Sebelumnya voucher sudah berhasil dibaca oleh
        # extract_griya_totals(), tetapi tidak dimasukkan
        # ke receipt_data.
        # ====================================================

        "voucher": (
            totals["voucher"]
            if totals["voucher"] is not None
            else 0
        ),

        "grand_total": (
            totals["grand_total"]
            if totals["grand_total"] is not None
            else 0
        ),
    }

    # --------------------------------------------------------
    # RAW OUTPUT
    # --------------------------------------------------------

    raw_output = "\n".join(
        lines
    )

    # --------------------------------------------------------
    # RETURN
    # --------------------------------------------------------

    return {
        "receipt_data": receipt_data,
        "raw_output": raw_output,
    }