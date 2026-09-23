import os
import base64
import time
import json

from dotenv import load_dotenv
from openai import OpenAI


# ==========================================
# 1. LOAD API KEY
# ==========================================

load_dotenv()

api_key = os.getenv("DEEPSEEK_API_KEY")

if not api_key:
    raise ValueError(
        "DEEPSEEK_API_KEY tidak ditemukan di .env"
    )

print("DeepSeek API key berhasil terbaca ✅")


# ==========================================
# 2. DEEPSEEK CLIENT
# ==========================================

client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com"
)


# ==========================================
# 3. ENCODE IMAGE
# ==========================================

def encode_image(image_path):

    with open(image_path, "rb") as image_file:

        return base64.b64encode(
            image_file.read()
        ).decode("utf-8")


# ==========================================
# 4. READ RECEIPT
# ==========================================

def read_receipt(image_path):

    image_base64 = encode_image(image_path)

    prompt = """
You are a receipt information extraction system.

Carefully analyze the receipt image.

Extract the following information:

1. merchant
2. items:
   - name
   - quantity
   - unit_price
   - total_price
3. subtotal
4. tax
5. service
6. grand_total

Rules:
- Read the numbers carefully.
- Do not invent information.
- If a field is not present, return null.
- Keep the original item meaning.
- Return ONLY valid JSON.
- Do not use markdown.
- Do not add explanations.

Use exactly this JSON structure:

{
    "merchant": "",
    "items": [
        {
            "name": "",
            "quantity": 0,
            "unit_price": 0,
            "total_price": 0
        }
    ],
    "subtotal": 0,
    "tax": null,
    "service": null,
    "grand_total": 0
}
"""

    start_time = time.perf_counter()

    response = client.chat.completions.create(
        model="deepseek-flash",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": (
                                "data:image/jpeg;base64,"
                                + image_base64
                            )
                        }
                    }
                ]
            }
        ]
    )

    end_time = time.perf_counter()

    inference_time = end_time - start_time

    result = response.choices[0].message.content

    return result, inference_time


# ==========================================
# 5. TEST RECEIPT 1
# ==========================================

print("\n" + "=" * 70)
print("TEST 1 — RECEIPT GRIYA BINTARA")
print("=" * 70)

receipt1 = "receipts/receipt1.jpeg"

result1, time1 = read_receipt(receipt1)

print("\nRAW OUTPUT:")
print(result1)

print(f"\nINFERENCE TIME: {time1:.2f} seconds")


# ==========================================
# 6. TEST RECEIPT 2
# ==========================================

print("\n" + "=" * 70)
print("TEST 2 — RECEIPT TEXAS CHICKEN")
print("=" * 70)

receipt2 = "receipts/receipt2.jpeg"

result2, time2 = read_receipt(receipt2)

print("\nRAW OUTPUT:")
print(result2)

print(f"\nINFERENCE TIME: {time2:.2f} seconds")