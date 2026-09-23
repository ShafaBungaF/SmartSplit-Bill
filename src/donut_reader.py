import re
import torch

from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_NAME = "naver-clova-ix/donut-base-finetuned-cord-v2"

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# ============================================================
# LOAD MODEL
# ============================================================

def load_donut_model():

    processor = DonutProcessor.from_pretrained(
        MODEL_NAME
    )

    model = VisionEncoderDecoderModel.from_pretrained(
        MODEL_NAME
    )

    model.to(DEVICE)
    model.eval()

    return processor, model


# ============================================================
# SAFE PRICE PARSER
# ============================================================

def parse_price(value):

    if value is None:
        return None

    if isinstance(value, (dict, list, tuple)):
        return None

    value = str(value).strip()

    if not value:
        return None

    # Jangan pernah mengubah timestamp menjadi harga.
    # Contoh:
    # 8:29:47 PM
    # 8:29:47
    if re.search(
        r"\d{1,2}:\d{2}:\d{2}",
        value
    ):
        return None

    # Jangan menerima teks yang jelas bukan harga.
    invalid_words = [
        "PM",
        "AM",
        "POS",
        "PRINT",
        "CASHIER",
        "SERVER",
        "PAX",
        "INVOICE",
        "ORDER",
        "DINE",
        "CARD",
        "MANDIRI",
        "CHANGE",
        "SURVEY",
        "KODE",
    ]

    upper_value = value.upper()

    for word in invalid_words:

        if word in upper_value:
            return None

    # Remove currency
    value = value.replace(
        "Rp",
        ""
    )

    value = value.replace(
        "rp",
        ""
    )

    value = value.replace(
        " ",
        ""
    )

    # Hanya angka dan pemisah harga
    if not re.fullmatch(
        r"[0-9.,]+",
        value
    ):
        return None

    # Ambil angka
    digits = re.sub(
        r"[^0-9]",
        "",
        value
    )

    if not digits:
        return None

    try:

        number = int(digits)

    except ValueError:

        return None

    # Proteksi nilai tidak masuk akal
    if number < 0:
        return None

    if number > 10_000_000_000:
        return None

    return number


# ============================================================
# SAFE QUANTITY PARSER
# ============================================================

def parse_quantity(value):

    if value is None:
        return None

    if isinstance(
        value,
        (dict, list, tuple)
    ):
        return None

    value = str(value).strip()

    # Jangan ambil angka dari timestamp
    if re.search(
        r"\d{1,2}:\d{2}:\d{2}",
        value
    ):
        return None

    # Quantity harus berupa angka sederhana
    match = re.fullmatch(
        r"\d+",
        value
    )

    if not match:
        return None

    try:

        number = int(value)

    except ValueError:

        return None

    if number < 1:
        return None

    if number > 9999:
        return None

    return number


# ============================================================
# CLEAN TEXT
# ============================================================

def clean_text(value):

    if value is None:
        return None

    if isinstance(
        value,
        (dict, list, tuple)
    ):
        return None

    value = str(value).strip()

    if not value:
        return None

    return value


# ============================================================
# PRODUCT VALIDATION
# ============================================================

def is_possible_product(item):

    if not isinstance(
        item,
        dict
    ):
        return False

    name = clean_text(
        item.get("nm")
    )

    if not name:
        return False

    upper_name = name.upper()

    # Informasi yang bukan produk
    excluded_keywords = [

        # Transaction
        "TOTAL",
        "SUBTOTAL",
        "SUB TOTAL",
        "INVOICE",
        "ORDER",

        # Staff
        "CASHIER",
        "SERVER",
        "PAX",

        # Dining
        "DINE IN",
        "TAKE AWAY",

        # Payment
        "PAYMENT",
        "MANDIRI",
        "CARD",
        "CASH",
        "CHANGE",

        # Discount / promo
        "VOUCHER",
        "DISCOUNT",
        "PROMO",
        "SURVEY",

        # Tax
        "PPN",
        "PB1",
        "TAX",
        "SERVICE",

        # Metadata
        "KODE",
        "ADDRESS",
        "TELP",
        "PHONE",

        # Location
        "PLAZA",
        "UNIT",

        # Date/time
        "AM",
        "PM",
    ]

    for keyword in excluded_keywords:

        if keyword in upper_name:
            return False

    return True


# ============================================================
# FIND MERCHANT
# ============================================================

def find_merchant(parsed):

    if not isinstance(
        parsed,
        dict
    ):
        return None

    # Donut CORD biasanya tidak memberikan
    # merchant dalam field khusus.
    #
    # Karena itu kita TIDAK akan menebak merchant
    # dari address/location.
    #
    # Jika merchant tidak jelas,
    # return None.

    merchant = parsed.get(
        "merchant"
    )

    if isinstance(
        merchant,
        str
    ):

        merchant = merchant.strip()

        if merchant:
            return merchant

    return None


# ============================================================
# EXTRACT MENU
# ============================================================

def extract_items(parsed):

    items = []

    if not isinstance(
        parsed,
        dict
    ):
        return items

    menu = parsed.get(
        "menu",
        []
    )

    if isinstance(
        menu,
        dict
    ):
        menu = [menu]

    if not isinstance(
        menu,
        list
    ):
        return items

    for raw_item in menu:

        if not is_possible_product(
            raw_item
        ):
            continue

        name = clean_text(
            raw_item.get("nm")
        )

        quantity = parse_quantity(
            raw_item.get("cnt")
        )

        unit_price = parse_price(
            raw_item.get("unitprice")
        )

        total_price = parse_price(
            raw_item.get("price")
        )

        # Harus punya minimal satu
        # informasi transaksi.
        if (
            quantity is None
            and unit_price is None
            and total_price is None
        ):
            continue

        items.append(
            {
                "name": name,
                "quantity": quantity,
                "unit_price": unit_price,
                "total_price": total_price,
            }
        )

    return items


# ============================================================
# EXTRACT SUMMARY
# ============================================================

def extract_summary(parsed):

    result = {
        "subtotal": None,
        "tax": None,
        "service_charge": None,
        "grand_total": None,
    }

    if not isinstance(
        parsed,
        dict
    ):
        return result


    # ========================================================
    # SUB TOTAL
    # ========================================================

    subtotal_section = parsed.get(
        "sub_total"
    )

    if isinstance(
        subtotal_section,
        dict
    ):

        subtotal = parse_price(
            subtotal_section.get(
                "subtotal_price"
            )
        )

        tax = parse_price(
            subtotal_section.get(
                "tax_price"
            )
        )

        service = parse_price(
            subtotal_section.get(
                "service_price"
            )
        )

        result["subtotal"] = subtotal

        result["tax"] = tax

        result["service_charge"] = service


    # ========================================================
    # TOTAL
    # ========================================================

    total_section = parsed.get(
        "total"
    )

    if isinstance(
        total_section,
        dict
    ):

        grand_total = parse_price(
            total_section.get(
                "total_price"
            )
        )

        result["grand_total"] = grand_total


    return result


# ============================================================
# CONVERT DONUT OUTPUT
# ============================================================

def convert_donut_output(parsed):

    summary = extract_summary(
        parsed
    )

    result = {

        "merchant": find_merchant(
            parsed
        ),

        "items": extract_items(
            parsed
        ),

        "subtotal": summary[
            "subtotal"
        ],

        "tax": summary[
            "tax"
        ],

        "service_charge": summary[
            "service_charge"
        ],

        "grand_total": summary[
            "grand_total"
        ],
    }

    return result


# ============================================================
# READ RECEIPT
# ============================================================

def read_receipt(
    image,
    processor,
    model
):

    # ========================================================
    # IMAGE
    # ========================================================

    if not isinstance(
        image,
        Image.Image
    ):

        image = Image.open(
            image
        )

    image = image.convert(
        "RGB"
    )


    # ========================================================
    # DONUT TASK
    # ========================================================

    task_prompt = "<s_cord-v2>"


    # ========================================================
    # DECODER INPUT
    # ========================================================

    decoder_input_ids = processor.tokenizer(
        task_prompt,
        add_special_tokens=False,
        return_tensors="pt"
    ).input_ids.to(
        DEVICE
    )


    # ========================================================
    # PROCESS IMAGE
    # ========================================================

    pixel_values = processor(
        image,
        return_tensors="pt"
    ).pixel_values.to(
        DEVICE
    )


    # ========================================================
    # INFERENCE
    # ========================================================

    with torch.no_grad():

        outputs = model.generate(

            pixel_values,

            decoder_input_ids=decoder_input_ids,

            max_length=model.decoder.config.max_position_embeddings,

            pad_token_id=processor.tokenizer.pad_token_id,

            eos_token_id=processor.tokenizer.eos_token_id,

            use_cache=True,

            num_beams=1,

            bad_words_ids=[
                [
                    processor.tokenizer.unk_token_id
                ]
            ],

            return_dict_in_generate=True,
        )


    # ========================================================
    # DECODE
    # ========================================================

    sequence = processor.batch_decode(
        outputs.sequences,
        skip_special_tokens=False
    )[0]


    sequence = sequence.replace(
        processor.tokenizer.eos_token,
        ""
    )

    sequence = sequence.replace(
        processor.tokenizer.pad_token,
        ""
    )

    sequence = sequence.strip()


    # ========================================================
    # TOKEN → JSON
    # ========================================================

    try:

        parsed = processor.token2json(
            sequence
        )

    except Exception:

        parsed = {}


    # ========================================================
    # SMARTSPLIT FORMAT
    # ========================================================

    receipt_data = convert_donut_output(
        parsed
    )


    # ========================================================
    # RETURN
    # ========================================================

    return {

        "receipt_data": receipt_data,

        "raw_output": sequence,

        "parsed_output": parsed,

    }