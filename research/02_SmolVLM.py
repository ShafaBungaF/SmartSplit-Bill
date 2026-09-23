import time
import torch
from pathlib import Path
from PIL import Image
from transformers import AutoProcessor, AutoModelForImageTextToText


# ============================================================
# 1. MODEL CONFIGURATION
# ============================================================

MODEL_NAME = "HuggingFaceTB/SmolVLM-500M-Instruct"

BASE_DIR = Path(__file__).resolve().parent.parent
RECEIPT_DIR = BASE_DIR / "receipts"

RECEIPTS = [
    {
        "name": "GRIYA BINTARA",
        "path": RECEIPT_DIR / "receipt1.jpeg"
    },
    {
        "name": "TEXAS CHICKEN",
        "path": RECEIPT_DIR / "receipt2.jpeg"
    }
]


# ============================================================
# 2. DEVICE
# ============================================================

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

print("=" * 70)
print("SMARTSPLIT BILL — SmolVLM RESEARCH")
print("=" * 70)
print(f"Model  : {MODEL_NAME}")
print(f"Device : {DEVICE}")
print("=" * 70)


# ============================================================
# 3. LOAD MODEL
# ============================================================

print("\nLoading processor...")
processor = AutoProcessor.from_pretrained(MODEL_NAME)

print("Loading model...")

model = AutoModelForImageTextToText.from_pretrained(
    MODEL_NAME,
    torch_dtype=torch.float32
)

model.to(DEVICE)
model.eval()

print("Model berhasil dimuat.")


# ============================================================
# 4. PROMPT
# ============================================================

PROMPT = """
Analyze this receipt carefully.

Extract ONLY the information that is actually visible on the receipt.

Return the result using exactly this structure:

{
  "merchant": null,
  "items": [
    {
      "name": null,
      "quantity": null,
      "unit_price": null,
      "total_price": null
    }
  ],
  "subtotal": null,
  "tax": null,
  "service_charge": null,
  "grand_total": null
}

Rules:

1. merchant = store or restaurant name.
2. items = only actual purchased products or food.
3. Do NOT include:
   - address
   - invoice number
   - cashier
   - payment method
   - promotional messages
   - survey messages
   - coupons
   - other non-product information
4. quantity = number of units purchased.
5. unit_price = price for one unit.
6. total_price = quantity multiplied by unit price, if visible.
7. subtotal = subtotal or total before tax, if visible.
8. tax = tax such as PPN or PB1, if visible.
9. service_charge = service charge, if visible.
10. grand_total = final amount paid.
11. Do not invent or guess information.
12. If information is not visible, use null.
13. Keep numbers as numbers without currency symbols or commas when possible.
14. Return ONLY the JSON object.
"""


# ============================================================
# 5. FUNCTION TO READ ONE RECEIPT
# ============================================================

def read_receipt(image_path):

    image = Image.open(image_path).convert("RGB")

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image"
                },
                {
                    "type": "text",
                    "text": PROMPT
                }
            ]
        }
    ]

    text = processor.apply_chat_template(
        messages,
        add_generation_prompt=True
    )

    inputs = processor(
        text=text,
        images=[image],
        return_tensors="pt"
    )

    inputs = {
        key: value.to(DEVICE)
        for key, value in inputs.items()
        if hasattr(value, "to")
    }

    # --------------------------------------------------------
    # Start inference timer
    # --------------------------------------------------------

    start_time = time.perf_counter()

    with torch.no_grad():
        generated_ids = model.generate(
            **inputs,
            max_new_tokens=400,
            do_sample=False
        )

    end_time = time.perf_counter()

    inference_time = end_time - start_time

    # --------------------------------------------------------
    # Decode result
    # --------------------------------------------------------

    generated_text = processor.batch_decode(
        generated_ids,
        skip_special_tokens=True
    )[0]

    return generated_text, inference_time


# ============================================================
# 6. TEST RECEIPTS
# ============================================================

results = []


for i, receipt in enumerate(RECEIPTS, start=1):

    print("\n")
    print("=" * 70)
    print(f"TEST {i} — {receipt['name']}")
    print("=" * 70)

    image_path = receipt["path"]

    print(f"Image : {image_path}")

    # Check image exists
    if not image_path.exists():
        print("ERROR: File receipt tidak ditemukan.")
        continue

    print("Status: File ditemukan.")

    try:

        result, inference_time = read_receipt(image_path)

        print("\nRESULT:")
        print("-" * 70)
        print(result)

        print("\nINFERENCE TIME:")
        print(f"{inference_time:.2f} seconds")

        results.append(
            {
                "name": receipt["name"],
                "inference_time": inference_time
            }
        )

    except Exception as e:

        print("\nERROR:")
        print(e)


# ============================================================
# 7. SUMMARY
# ============================================================

print("\n")
print("=" * 70)
print("SMOLVLM RESEARCH SUMMARY")
print("=" * 70)

for result in results:

    print(
        f"{result['name']:<20} : "
        f"{result['inference_time']:.2f} seconds"
    )

if results:

    average_time = sum(
        result["inference_time"]
        for result in results
    ) / len(results)

    print("-" * 70)
    print(
        f"{'AVERAGE':<20} : "
        f"{average_time:.2f} seconds"
    )

print("=" * 70)