# SmartSplit Bill

SmartSplit Bill adalah prototype web untuk membaca struk menggunakan AI dan membagi tagihan secara otomatis.

## Features

- Upload foto struk
- AI receipt reading
- Edit hasil pembacaan
- Split item ke beberapa orang
- Perhitungan Tax/PPN, service, dan voucher
- Validasi grand total

## Tech Stack

- Python
- Streamlit
- PaddleOCR
- PaddlePaddle

## Model Comparison
- Donut --> avg = 15.75s
- SmolVLM --> avg = 83.21s
- PaddleOCR-VL --> avg = 34.62s
-PaddleOCR --> avg = 508.24s

## Selected Model

**PaddleOCR** dipilih untuk prototype berdasarkan hasil pengujian pada dua receipt karena dapat membaca informasi transaksi yang dibutuhkan dan memiliki waktu inference lebih rendah dibandingkan PaddleOCR-VL pada CPU yang digunakan.

## Example Results

### Texas Chicken
- Item: 4 Combo 1 Original HBB
- Subtotal: Rp174.545
- PB1: Rp17.455
- Grand Total: Rp192.000

### Griya Bintara
- G-BENG MAXX 32G: 7 × Rp6.400
- MINERALE 600 ML: 7 × Rp3.600
- Voucher: Rp3.900
- PPN: Rp6.937
- Grand Total: Rp66.100

## Evaluation

### Strengths
- Alur upload → cek data → bagi item → hasil
- Data dapat diedit sebelum split
- Mendukung pembagian item dan validasi total

### Weaknesses
- Parser belum generic untuk semua receipt
- OCR masih dapat salah membaca
- Inference time bergantung pada perangkat

### Future Improvements
- Generic receipt parser
- Confidence score
- More receipt testing
- Flexible split
- Export Excel/PDF