import time
from pathlib import Path

from paddleocr import PaddleOCRVL


# ============================================================
# 1. PATH CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
RECEIPT_DIR = BASE_DIR / "receipts"

RECEIPTS = [
    {
        "name": "TEXAS CHICKEN",
        "path": RECEIPT_DIR / "receipt1.jpeg"
    },
    {
        "name": "GRIYA BINTARA",
        "path": RECEIPT_DIR / "receipt2.jpeg"
    }
]


# ============================================================
# 2. MODEL CONFIGURATION
# ============================================================

print("=" * 70)
print("SMARTSPLIT BILL — PaddleOCR-VL RESEARCH")
print("=" * 70)

print("Model : PaddleOCR-VL-1.6")
print("Device: CPU")
print("=" * 70)


# ============================================================
# 3. LOAD MODEL
# ============================================================

print("\nLoading PaddleOCR-VL-1.6...")
print("First run may take some time because model files need to be downloaded.")

pipeline = PaddleOCRVL(
    pipeline_version="v1.6"
)

print("PaddleOCR-VL berhasil dimuat.")


# ============================================================
# 4. PROCESS RECEIPTS
# ============================================================

results = []


for i, receipt in enumerate(RECEIPTS, start=1):

    print("\n")
    print("=" * 70)
    print(f"TEST {i} — {receipt['name']}")
    print("=" * 70)

    image_path = receipt["path"]

    print(f"Image : {image_path}")

    if not image_path.exists():
        print("ERROR: File receipt tidak ditemukan.")
        continue

    print("Status: File ditemukan.")

    try:

        # ----------------------------------------------------
        # Start inference timer
        # ----------------------------------------------------

        start_time = time.perf_counter()

        output = pipeline.predict(
            str(image_path)
        )

        end_time = time.perf_counter()

        inference_time = end_time - start_time

        # ----------------------------------------------------
        # Print result
        # ----------------------------------------------------

        print("\nRESULT:")
        print("-" * 70)

        for res in output:

            try:
                res.print()

            except Exception:

                print(res)

        # ----------------------------------------------------
        # Inference time
        # ----------------------------------------------------

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
        print(type(e).__name__, ":", e)


# ============================================================
# 5. SUMMARY
# ============================================================

print("\n")
print("=" * 70)
print("PADDLEOCR-VL RESEARCH SUMMARY")
print("=" * 70)

if results:

    for result in results:

        print(
            f"{result['name']:<20} : "
            f"{result['inference_time']:.2f} seconds"
        )

    average_time = sum(
        result["inference_time"]
        for result in results
    ) / len(results)

    print("-" * 70)

    print(
        f"{'AVERAGE':<20} : "
        f"{average_time:.2f} seconds"
    )

else:

    print("Tidak ada hasil pengujian.")

print("=" * 70)