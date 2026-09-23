import os
import time
from paddleocr import PaddleOCR


# ============================================================
# INITIALIZE PADDLEOCR
# ============================================================

print("=" * 70)
print("INITIALIZING PADDLEOCR")
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
# FUNCTION: TEST ONE RECEIPT
# ============================================================

def test_receipt(receipt_name, image_path):

    print("\n" + "=" * 70)
    print(f"TEST — {receipt_name}")
    print("=" * 70)

    print(f"Image : {image_path}")

    if not os.path.exists(image_path):
        print("Status: FILE TIDAK DITEMUKAN")
        return None

    print("Status: File ditemukan.")
    print("\nRunning PaddleOCR...")
    print("Mohon tunggu...\n")

    start_time = time.time()

    result = ocr.predict(image_path)

    elapsed = time.time() - start_time

    print("Inference selesai.")

    print("\n" + "-" * 70)
    print("OUTPUT")
    print("-" * 70)

    # Print OCR result
    for res in result:
        try:
            res.print()
        except Exception:
            print(res)

    print("\n" + "-" * 70)
    print(f"INFERENCE TIME: {elapsed:.2f} seconds")
    print("-" * 70)

    return elapsed


# ============================================================
# RECEIPT PATHS
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
# TEST RECEIPT 1
# TEXAS CHICKEN
# ============================================================

time1 = test_receipt(
    "RECEIPT 1 — TEXAS CHICKEN",
    receipt1
)


# ============================================================
# TEST RECEIPT 2
# GRIYA BINTARA
# ============================================================

time2 = test_receipt(
    "RECEIPT 2 — GRIYA BINTARA",
    receipt2
)


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("PADDLEOCR SUMMARY")
print("=" * 70)

if time1 is not None:
    print(f"TEXAS CHICKEN : {time1:.2f} seconds")

if time2 is not None:
    print(f"GRIYA BINTARA : {time2:.2f} seconds")

times = [
    t for t in [time1, time2]
    if t is not None
]

if times:
    average = sum(times) / len(times)

    print("-" * 70)
    print(f"AVERAGE       : {average:.2f} seconds")

print("=" * 70)