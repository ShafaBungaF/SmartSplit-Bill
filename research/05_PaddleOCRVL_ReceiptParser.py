import os
import time

from paddleocr import PaddleOCRVL


# ============================================================
# CONFIG
# ============================================================

MODEL_NAME = "PaddleOCR-VL-1.6"

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

RECEIPT_1 = os.path.join(
    BASE_DIR,
    "receipts",
    "receipt1.jpeg"
)

RECEIPT_2 = os.path.join(
    BASE_DIR,
    "receipts",
    "receipt2.jpeg"
)


# ============================================================
# HEADER
# ============================================================

print("=" * 70)
print("SMARTSPLIT BILL — PaddleOCR-VL OPTIMIZATION TEST")
print("=" * 70)
print(f"Model  : {MODEL_NAME}")
print("Device : CPU")
print("Layout : DISABLED")
print("=" * 70)


# ============================================================
# LOAD MODEL
# ============================================================

print()
print("Loading PaddleOCR-VL-1.6...")
print()

pipeline = PaddleOCRVL(
    pipeline_version="v1.6",
    use_layout_detection=False,
    use_chart_recognition=False,
    use_seal_recognition=False,
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
)

print()
print("Model berhasil dimuat.")
print()


# ============================================================
# TEST FUNCTION
# ============================================================

def test_receipt(
    image_path,
    receipt_name
):

    print("=" * 70)
    print(f"TEST — {receipt_name}")
    print("=" * 70)

    print(f"Image : {image_path}")

    if not os.path.exists(image_path):

        print("Status: FILE TIDAK DITEMUKAN")
        return None

    print("Status: File ditemukan.")
    print()

    print("Running PaddleOCR-VL...")
    print("Mohon tunggu...")
    print()

    start_time = time.perf_counter()

    try:

        output = pipeline.predict(
            image_path,

            # Pastikan opsi tetap aktif
            # pada proses prediction.
            use_layout_detection=False,
            use_chart_recognition=False,
            use_seal_recognition=False,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,

            # Batasi output agar tidak terlalu panjang
            max_new_tokens=512,
        )

        elapsed = (
            time.perf_counter()
            - start_time
        )

        print()
        print("Inference selesai.")
        print()

        print("-" * 70)
        print("OUTPUT")
        print("-" * 70)

        for result in output:

            # Gunakan print bawaan PaddleOCR
            # supaya output lebih mudah dibaca.
            try:

                result.print()

            except Exception:

                print(result)

            print()


        print("-" * 70)
        print(
            f"INFERENCE TIME: {elapsed:.2f} seconds"
        )
        print("-" * 70)

        return elapsed


    except Exception as e:

        elapsed = (
            time.perf_counter()
            - start_time
        )

        print()
        print("ERROR:")
        print(str(e))
        print()
        print(
            f"Elapsed time: {elapsed:.2f} seconds"
        )

        return None


# ============================================================
# TEST 1 — TEXAS CHICKEN
# ============================================================

time_1 = test_receipt(
    RECEIPT_1,
    "RECEIPT 1 — TEXAS CHICKEN"
)


# ============================================================
# TEST 2 — GRIYA BINTARA
# ============================================================

time_2 = test_receipt(
    RECEIPT_2,
    "RECEIPT 2 — GRIYA BINTARA"
)


# ============================================================
# SUMMARY
# ============================================================

print()
print("=" * 70)
print("PADDLEOCR-VL OPTIMIZATION SUMMARY")
print("=" * 70)

if time_1 is not None:

    print(
        f"TEXAS CHICKEN : {time_1:.2f} seconds"
    )

else:

    print(
        "TEXAS CHICKEN : FAILED"
    )


if time_2 is not None:

    print(
        f"GRIYA BINTARA : {time_2:.2f} seconds"
    )

else:

    print(
        "GRIYA BINTARA : FAILED"
    )


if (
    time_1 is not None
    and time_2 is not None
):

    average = (
        time_1 + time_2
    ) / 2

    print("-" * 70)
    print(
        f"AVERAGE       : {average:.2f} seconds"
    )


print("=" * 70)