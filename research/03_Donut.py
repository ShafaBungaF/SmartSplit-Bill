import time
import re
from pathlib import Path

import torch
from PIL import Image
from transformers import DonutProcessor, VisionEncoderDecoderModel


# ============================================================
# 1. MODEL CONFIGURATION
# ============================================================

MODEL_NAME = "naver-clova-ix/donut-base-finetuned-cord-v2"

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
print("SMARTSPLIT BILL — Donut RESEARCH")
print("=" * 70)
print(f"Model  : {MODEL_NAME}")
print(f"Device : {DEVICE}")
print("=" * 70)


# ============================================================
# 3. LOAD PROCESSOR
# ============================================================

print("\nLoading processor...")

processor = DonutProcessor.from_pretrained(
    MODEL_NAME
)

print("Processor berhasil dimuat.")


# ============================================================
# 4. LOAD MODEL
# ============================================================

print("Loading model...")

model = VisionEncoderDecoderModel.from_pretrained(
    MODEL_NAME
)

model.to(DEVICE)
model.eval()

print("Model berhasil dimuat.")


# ============================================================
# 5. DONUT TASK PROMPT
# ============================================================

TASK_PROMPT = "<s_cord-v2>"


# ============================================================
# 6. FUNCTION TO READ ONE RECEIPT
# ============================================================

def read_receipt(image_path):

    image = Image.open(image_path).convert("RGB")

    # --------------------------------------------------------
    # Prepare decoder prompt
    # --------------------------------------------------------

    decoder_input_ids = processor.tokenizer(
        TASK_PROMPT,
        add_special_tokens=False,
        return_tensors="pt"
    ).input_ids.to(DEVICE)

    # --------------------------------------------------------
    # Process image
    # --------------------------------------------------------

    pixel_values = processor(
        image,
        return_tensors="pt"
    ).pixel_values.to(DEVICE)

    # --------------------------------------------------------
    # Start inference timer
    # --------------------------------------------------------

    start_time = time.perf_counter()

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
                [processor.tokenizer.unk_token_id]
            ],
            return_dict_in_generate=True
        )

    end_time = time.perf_counter()

    inference_time = end_time - start_time

    # --------------------------------------------------------
    # Decode result
    # --------------------------------------------------------

    sequence = processor.batch_decode(
        outputs.sequences,
        skip_special_tokens=False
    )[0]

    # Remove EOS and PAD tokens
    sequence = sequence.replace(
        processor.tokenizer.eos_token,
        ""
    )

    sequence = sequence.replace(
        processor.tokenizer.pad_token,
        ""
    )

    sequence = sequence.strip()

    # --------------------------------------------------------
    # Convert Donut output to JSON-like dictionary
    # --------------------------------------------------------

    try:

        prediction = processor.token2json(
            sequence
        )

    except Exception as e:

        prediction = None

        print("\nWarning:")
        print("Gagal mengubah output Donut menjadi JSON.")
        print("Error:", e)

    return sequence, prediction, inference_time


# ============================================================
# 7. RUN TESTS
# ============================================================

results = []


for i, receipt in enumerate(RECEIPTS, start=1):

    print("\n")
    print("=" * 70)
    print(f"TEST {i} — {receipt['name']}")
    print("=" * 70)

    image_path = receipt["path"]

    print(f"Image : {image_path}")

    # Check image
    if not image_path.exists():

        print("ERROR: File receipt tidak ditemukan.")

        continue

    print("Status: File ditemukan.")

    try:

        raw_output, prediction, inference_time = read_receipt(
            image_path
        )

        # ----------------------------------------------------
        # RAW OUTPUT
        # ----------------------------------------------------

        print("\nRAW DONUT OUTPUT:")
        print("-" * 70)
        print(raw_output)

        # ----------------------------------------------------
        # PARSED OUTPUT
        # ----------------------------------------------------

        print("\nPARSED OUTPUT:")
        print("-" * 70)

        if prediction is not None:
            print(prediction)
        else:
            print("Tidak berhasil diparse.")

        # ----------------------------------------------------
        # INFERENCE TIME
        # ----------------------------------------------------

        print("\nINFERENCE TIME:")
        print(f"{inference_time:.2f} seconds")

        results.append(
            {
                "name": receipt["name"],
                "inference_time": inference_time,
                "prediction": prediction
            }
        )

    except Exception as e:

        print("\nERROR:")
        print(type(e).__name__, ":", e)


# ============================================================
# 8. SUMMARY
# ============================================================

print("\n")
print("=" * 70)
print("DONUT RESEARCH SUMMARY")
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