import streamlit as st
from PIL import Image

from src.paddle_reader import (
    load_paddle_model,
    read_receipt,
)


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="SmartSplit Bill",
    page_icon="🧾",
    layout="wide",
)


# =========================================================
# CUSTOM CSS
# =========================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 38px;
        font-weight: 700;
        color: #222222;
        margin-bottom: 4px;
    }

    .subtitle {
        font-size: 16px;
        color: #666666;
        margin-bottom: 25px;
    }

    .step-active {
        background-color: #dff5e7;
        color: #16803c;
        padding: 9px 14px;
        border-radius: 20px;
        text-align: center;
        font-size: 14px;
        font-weight: 600;
    }

    .step-inactive {
        background-color: #f1f3f5;
        color: #666666;
        padding: 9px 14px;
        border-radius: 20px;
        text-align: center;
        font-size: 14px;
    }

    .arrow {
        text-align: center;
        color: #999999;
        font-size: 20px;
        padding-top: 5px;
    }

    .file-info {
        background-color: #f8f9fa;
        padding: 18px;
        border-radius: 10px;
        line-height: 1.6;
    }

    .item-card {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 12px;
    }

    .result-card {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 15px;
    }

    .total-result {
        font-size: 28px;
        font-weight: 700;
    }

    section[data-testid="stSidebar"] {
        background-color: #f4f6f8;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# SESSION STATE
# =========================================================

if "step" not in st.session_state:
    st.session_state.step = 1

if "receipt_data" not in st.session_state:
    st.session_state.receipt_data = None

if "raw_output" not in st.session_state:
    st.session_state.raw_output = None

if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = None

if "people" not in st.session_state:
    st.session_state.people = ["Orang 1", "Orang 2"]

if "assignments" not in st.session_state:
    st.session_state.assignments = {}


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def format_rupiah(value):
    """
    Format angka menjadi Rupiah.
    Contoh:
    192000 -> Rp 192.000
    """

    try:
        value = int(round(value))
    except:
        value = 0

    return f"Rp {value:,}".replace(",", ".")


def get_numeric(data, key, default=0):
    """
    Mengambil angka dari dictionary secara aman.
    """

    value = data.get(key, default)

    if isinstance(value, (int, float)):
        return value

    try:
        return float(value)
    except:
        return default


def get_item_total(item):
    """
    Mengambil total harga item.
    """

    value = item.get(
        "total_price",
        0,
    )

    if isinstance(value, (int, float)):
        return float(value)

    try:
        return float(value)
    except:
        return 0.0


def calculate_split(data, people, assignments):
    """
    Menghitung pembagian bill.

    Setiap item dibagi rata kepada orang yang
    dipilih untuk item tersebut.

    Kemudian hasil item dialokasikan terhadap
    grand total receipt agar total akhirnya
    selalu sama persis dengan grand total.
    """

    items = data.get(
        "items",
        [],
    )

    grand_total = get_numeric(
        data,
        "grand_total",
        0,
    )

    person_item_subtotals = {
        person: 0.0
        for person in people
    }

    person_items = {
        person: []
        for person in people
    }

    # -----------------------------------------------------
    # Hitung total semua item
    # -----------------------------------------------------

    all_items_total = sum(
        get_item_total(item)
        for item in items
    )

    # -----------------------------------------------------
    # Hitung share setiap orang
    # -----------------------------------------------------

    for i, item in enumerate(items):

        item_total = get_item_total(item)

        assigned_people = assignments.get(
            i,
            [],
        )

        if not assigned_people:
            continue

        share = (
            item_total
            / len(assigned_people)
        )

        for person in assigned_people:

            person_item_subtotals[person] += share

            person_items[person].append(
                {
                    "name": item.get(
                        "name",
                        f"Item {i + 1}",
                    ),
                    "amount": share,
                }
            )

    assigned_items_total = sum(
        person_item_subtotals.values()
    )

    # -----------------------------------------------------
    # Sesuaikan dengan grand total
    #
    # Contoh Texas:
    #
    # Item total   = 174.545
    # Grand total  = 192.000
    #
    # Ada tambahan PB1 sebesar 17.455.
    #
    # Contoh Griya:
    #
    # Item total   = 70.000
    # Grand total  = 66.100
    #
    # Ada voucher 3.900.
    #
    # Dengan faktor ini, keduanya bisa ditangani
    # tanpa double-counting.
    # -----------------------------------------------------

    person_totals = {
        person: 0.0
        for person in people
    }

    if assigned_items_total > 0:

        adjustment_factor = (
            grand_total
            / assigned_items_total
        )

        for person in people:

            person_totals[person] = (
                person_item_subtotals[person]
                * adjustment_factor
            )

    # -----------------------------------------------------
    # Informasi penyesuaian
    # -----------------------------------------------------

    total_adjustment = (
        grand_total
        - all_items_total
    )

    return {
        "person_item_subtotals": person_item_subtotals,
        "person_totals": person_totals,
        "person_items": person_items,
        "all_items_total": all_items_total,
        "assigned_items_total": assigned_items_total,
        "grand_total": grand_total,
        "total_adjustment": total_adjustment,
    }


def round_split_totals(
    person_totals,
    grand_total,
):
    """
    Membulatkan hasil split ke rupiah terdekat
    dan memastikan total akhirnya sama dengan
    grand total.
    """

    rounded = {
        person: int(round(amount))
        for person, amount in person_totals.items()
    }

    difference = (
        int(round(grand_total))
        - sum(rounded.values())
    )

    if difference != 0 and rounded:

        target_person = max(
            rounded,
            key=rounded.get,
        )

        rounded[target_person] += difference

    return rounded


def calculate_item_display(
    item_total,
    all_items_total,
    grand_total,
    tax,
    voucher,
    service_charge,
):
    """
    Menentukan informasi yang ditampilkan untuk
    setiap item.

    Tidak semua nota memiliki struktur pajak yang sama.

    Karena itu:
    - Jika grand total lebih besar dari item total,
      selisih dianggap sebagai tambahan biaya.
    - Jika grand total lebih kecil dari item total,
      selisih dianggap sebagai diskon/voucher.
    - Tax tetap ditampilkan sebagai informasi jika
      tersedia.
    """

    if all_items_total <= 0:

        return {
            "tax_allocated": 0,
            "voucher_allocated": 0,
            "service_allocated": 0,
            "final_total": item_total,
        }

    # Proporsi item terhadap seluruh item
    proportion = (
        item_total
        / all_items_total
    )

    # -----------------------------------------------------
    # Total adjustment
    #
    # Ini yang benar-benar menentukan grand total.
    # -----------------------------------------------------

    adjustment = (
        grand_total
        - all_items_total
    )

    # -----------------------------------------------------
    # Jika adjustment positif:
    # ada tambahan biaya.
    #
    # Jika adjustment negatif:
    # ada pengurangan/diskon.
    # -----------------------------------------------------

    if adjustment > 0:

        additional_cost = (
            adjustment
            * proportion
        )

        final_total = (
            item_total
            + additional_cost
        )

        voucher_allocated = 0

    elif adjustment < 0:

        voucher_allocated = (
            abs(adjustment)
            * proportion
        )

        final_total = (
            item_total
            - voucher_allocated
        )

    else:

        voucher_allocated = 0

        final_total = item_total

    # -----------------------------------------------------
    # Tax ditampilkan sebagai informasi.
    #
    # Tetapi jangan selalu ditambahkan lagi ke final_total,
    # karena beberapa receipt seperti Griya sudah mencetak
    # PPN sebagai informasi dalam total belanja.
    # -----------------------------------------------------

    tax_allocated = (
        tax
        * proportion
        if tax > 0
        else 0
    )

    service_allocated = (
        service_charge
        * proportion
        if service_charge > 0
        else 0
    )

    return {
        "tax_allocated": tax_allocated,
        "voucher_allocated": voucher_allocated,
        "service_allocated": service_allocated,
        "final_total": final_total,
    }


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.markdown(
        "## 🧾 SmartSplit Bill"
    )

    st.markdown("---")

    st.markdown(
        "### AI Model"
    )

    selected_model = st.selectbox(
        "Model",
        ["PaddleOCR"],
        index=0,
    )

    st.markdown(
        "### Currency"
    )

    selected_currency = st.selectbox(
        "Currency",
        ["IDR (Rp)"],
        index=0,
    )

    st.markdown("---")

    st.success(
        "AI Ready"
    )


# =========================================================
# HEADER
# =========================================================

st.markdown(
    '<div class="main-title">'
    'SmartSplit Bill'
    '</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    'Foto struknya, biar AI yang baca, lalu bagi tagihan '
    'dengan adil sampai ke rupiah terakhir.'
    '</div>',
    unsafe_allow_html=True,
)


# =========================================================
# STEPPER
# =========================================================

step1, arrow1, step2, arrow2, step3, arrow3, step4 = st.columns(
    [
        2.2,
        0.4,
        2.2,
        0.4,
        2.2,
        0.4,
        2.2,
    ]
)


with step1:

    if st.session_state.step == 1:

        st.markdown(
            '<div class="step-active">'
            '1. Upload nota'
            '</div>',
            unsafe_allow_html=True,
        )

    else:

        st.markdown(
            '<div class="step-inactive">'
            '1. Upload nota'
            '</div>',
            unsafe_allow_html=True,
        )


with arrow1:

    st.markdown(
        '<div class="arrow">→</div>',
        unsafe_allow_html=True,
    )


with step2:

    if st.session_state.step == 2:

        st.markdown(
            '<div class="step-active">'
            '2. Cek data'
            '</div>',
            unsafe_allow_html=True,
        )

    else:

        st.markdown(
            '<div class="step-inactive">'
            '2. Cek data'
            '</div>',
            unsafe_allow_html=True,
        )


with arrow2:

    st.markdown(
        '<div class="arrow">→</div>',
        unsafe_allow_html=True,
    )


with step3:

    if st.session_state.step == 3:

        st.markdown(
            '<div class="step-active">'
            '3. Bagi item'
            '</div>',
            unsafe_allow_html=True,
        )

    else:

        st.markdown(
            '<div class="step-inactive">'
            '3. Bagi item'
            '</div>',
            unsafe_allow_html=True,
        )


with arrow3:

    st.markdown(
        '<div class="arrow">→</div>',
        unsafe_allow_html=True,
    )


with step4:

    if st.session_state.step == 4:

        st.markdown(
            '<div class="step-active">'
            '4. Hasil'
            '</div>',
            unsafe_allow_html=True,
        )

    else:

        st.markdown(
            '<div class="step-inactive">'
            '4. Hasil'
            '</div>',
            unsafe_allow_html=True,
        )


# =========================================================
# STEP 1
# UPLOAD NOTA
# =========================================================

if st.session_state.step == 1:

    st.markdown(
        "## 1. Upload nota"
    )

    st.write(
        "Upload foto nota yang ingin dibagi. "
        "Format yang didukung: JPG, JPEG, dan PNG."
    )

    uploaded_file = st.file_uploader(
        "Upload foto nota",
        type=[
            "jpg",
            "jpeg",
            "png",
        ],
        label_visibility="collapsed",
    )

    if uploaded_file is not None:

        st.session_state.uploaded_file_name = (
            uploaded_file.name
        )

        st.success(
            f"Nota berhasil dipilih: "
            f"{uploaded_file.name}"
        )

        col1, col2 = st.columns(
            [1.2, 1],
            gap="large",
        )

        with col1:

            st.markdown(
                "### Preview nota"
            )

            st.image(
                uploaded_file,
                use_container_width=True,
            )

        with col2:

            st.markdown(
                "### Informasi file"
            )

            st.markdown(
                f"""
                <div class="file-info">

                <b>Nama file</b><br>
                {uploaded_file.name}

                <br><br>

                <b>Tipe file</b><br>
                {uploaded_file.type}

                <br><br>

                <b>Ukuran</b><br>
                {uploaded_file.size / 1024:.1f} KB

                </div>
                """,
                unsafe_allow_html=True,
            )

            st.write("")

            if st.button(
                "🔍 Baca nota dengan AI",
                type="primary",
                use_container_width=True,
            ):

                try:

                    with st.spinner(
                        "AI sedang membaca nota... "
                        "Proses dapat membutuhkan sekitar "
                        "30 detik."
                    ):

                        ocr = load_paddle_model()

                        uploaded_file.seek(0)

                        image = Image.open(
                            uploaded_file
                        ).convert("RGB")

                        result = read_receipt(
                            image,
                            ocr,
                        )

                        st.session_state.receipt_data = (
                            result["receipt_data"]
                        )

                        st.session_state.raw_output = (
                            result["raw_output"]
                        )

                        st.session_state.step = 2

                    st.rerun()

                except Exception as e:

                    st.error(
                        "Terjadi error saat membaca nota."
                    )

                    st.exception(e)

            if st.button(
                "✏️ Isi manual tanpa AI",
                use_container_width=True,
            ):

                st.session_state.receipt_data = {
                    "merchant": "",
                    "items": [],
                    "subtotal": 0,
                    "tax": 0,
                    "service_charge": 0,
                    "voucher": 0,
                    "grand_total": 0,
                }

                st.session_state.raw_output = None

                st.session_state.step = 2

                st.rerun()


# =========================================================
# STEP 2
# CEK DATA
# =========================================================

if st.session_state.step == 2:

    st.markdown(
        "## 2. Cek data"
    )

    st.info(
        "Periksa hasil pembacaan AI. "
        "Semua data dapat diedit sebelum melanjutkan."
    )

    data = st.session_state.receipt_data

    if data is None:

        st.warning(
            "Belum ada data receipt."
        )

    else:

        # -------------------------------------------------
        # MERCHANT
        # -------------------------------------------------

        merchant_value = data.get(
            "merchant",
            "",
        )

        if not isinstance(
            merchant_value,
            str,
        ):
            merchant_value = ""

        merchant = st.text_input(
            "Nama merchant",
            value=merchant_value,
            key="merchant_input",
        )

        # -------------------------------------------------
        # ITEMS
        # -------------------------------------------------

        st.markdown(
            "### Item"
        )

        items = data.get(
            "items",
            [],
        )

        if not isinstance(
            items,
            list,
        ):
            items = []

        items_to_delete = None

        for i, item in enumerate(items):

            if not isinstance(
                item,
                dict,
            ):

                item = {
                    "name": "",
                    "quantity": 1,
                    "unit_price": 0,
                    "total_price": 0,
                }

                items[i] = item

            st.markdown(
                f"**Item {i + 1}**"
            )

            col1, col2, col3, col4, col5 = st.columns(
                [
                    2.2,
                    1,
                    1.5,
                    1.5,
                    0.6,
                ]
            )

            with col1:

                name_value = item.get(
                    "name",
                    "",
                )

                if not isinstance(
                    name_value,
                    str,
                ):
                    name_value = ""

                item["name"] = st.text_input(
                    "Nama",
                    value=name_value,
                    key=f"name_{i}",
                )

            with col2:

                qty_value = item.get(
                    "quantity",
                    1,
                )

                if not isinstance(
                    qty_value,
                    int,
                ):
                    qty_value = 1

                if qty_value < 1:
                    qty_value = 1

                if qty_value > 9999:
                    qty_value = 1

                item["quantity"] = st.number_input(
                    "Qty",
                    min_value=1,
                    max_value=9999,
                    value=qty_value,
                    step=1,
                    key=f"qty_{i}",
                )

            with col3:

                unit_value = item.get(
                    "unit_price",
                    0,
                )

                if not isinstance(
                    unit_value,
                    int,
                ):
                    unit_value = 0

                if unit_value < 0:
                    unit_value = 0

                item["unit_price"] = st.number_input(
                    "Harga satuan",
                    min_value=0,
                    max_value=10_000_000_000,
                    value=unit_value,
                    step=100,
                    key=f"unit_{i}",
                )

            with col4:

                total_value = item.get(
                    "total_price",
                    0,
                )

                if not isinstance(
                    total_value,
                    int,
                ):
                    total_value = 0

                if total_value < 0:
                    total_value = 0

                item["total_price"] = st.number_input(
                    "Total",
                    min_value=0,
                    max_value=10_000_000_000,
                    value=total_value,
                    step=100,
                    key=f"total_{i}",
                )

            with col5:

                st.write("")

                if st.button(
                    "🗑️",
                    key=f"delete_{i}",
                    help="Hapus item",
                ):

                    items_to_delete = i

        if items_to_delete is not None:

            items.pop(
                items_to_delete
            )

            st.session_state.receipt_data[
                "items"
            ] = items

            st.rerun()

        if st.button(
            "＋ Tambah item",
        ):

            items.append(
                {
                    "name": "",
                    "quantity": 1,
                    "unit_price": 0,
                    "total_price": 0,
                }
            )

            st.session_state.receipt_data[
                "items"
            ] = items

            st.rerun()

        # -------------------------------------------------
        # SUMMARY
        # -------------------------------------------------

        st.markdown(
            "### Ringkasan transaksi"
        )

        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:

            subtotal_value = data.get(
                "subtotal",
                0,
            )

            if not isinstance(
                subtotal_value,
                int,
            ):
                subtotal_value = 0

            subtotal = st.number_input(
                "Subtotal",
                min_value=0,
                max_value=10_000_000_000,
                value=subtotal_value,
                step=100,
                key="subtotal_input",
            )

        with col2:

            tax_value = data.get(
                "tax",
                0,
            )

            if not isinstance(
                tax_value,
                int,
            ):
                tax_value = 0

            tax = st.number_input(
                "Tax / PPN / PB1",
                min_value=0,
                max_value=10_000_000_000,
                value=tax_value,
                step=100,
                key="tax_input",
            )

        with col3:

            service_value = data.get(
                "service_charge",
                0,
            )

            if not isinstance(
                service_value,
                int,
            ):
                service_value = 0

            service = st.number_input(
                "Service charge",
                min_value=0,
                max_value=10_000_000_000,
                value=service_value,
                step=100,
                key="service_input",
            )

        with col4:

            voucher_value = data.get(
                "voucher",
                0,
            )

            if not isinstance(
                voucher_value,
                int,
            ):
                voucher_value = 0

            voucher = st.number_input(
                "Voucher",
                min_value=0,
                max_value=10_000_000_000,
                value=voucher_value,
                step=100,
                key="voucher_input",
            )

        with col5:

            grand_total_value = data.get(
                "grand_total",
                0,
            )

            if not isinstance(
                grand_total_value,
                int,
            ):
                grand_total_value = 0

            grand_total = st.number_input(
                "Grand total",
                min_value=0,
                max_value=10_000_000_000,
                value=grand_total_value,
                step=100,
                key="grand_total_input",
            )

        # -------------------------------------------------
        # SAVE DATA
        # -------------------------------------------------

        st.session_state.receipt_data = {
            "merchant": merchant,
            "items": items,
            "subtotal": subtotal,
            "tax": tax,
            "service_charge": service,
            "voucher": voucher,
            "grand_total": grand_total,
        }

        st.markdown("")

        if st.button(
            "Lanjut ke Bagi Item →",
            type="primary",
            use_container_width=True,
        ):

            # Jangan reset assignments jika kembali
            # dari Step 3.
            if not st.session_state.assignments:

                st.session_state.assignments = {}

            st.session_state.step = 3

            st.rerun()

        with st.expander(
            "Lihat raw output PaddleOCR"
        ):

            st.code(
                st.session_state.raw_output or "",
                language="text",
            )


# =========================================================
# STEP 3
# BAGI ITEM
# =========================================================

if st.session_state.step == 3:

    st.markdown(
        "## 3. Bagi item"
    )

    st.info(
        "Tambahkan orang yang ikut patungan, "
        "kemudian pilih siapa yang membayar setiap item."
    )

    data = st.session_state.receipt_data

    if data is None:

        st.warning(
            "Data receipt belum tersedia."
        )

    else:

        # -------------------------------------------------
        # RECEIPT SUMMARY
        # -------------------------------------------------

        merchant = data.get(
            "merchant",
            "-",
        )

        grand_total = get_numeric(
            data,
            "grand_total",
            0,
        )

        items = data.get(
            "items",
            [],
        )

        tax = get_numeric(
            data,
            "tax",
            0,
        )

        voucher = get_numeric(
            data,
            "voucher",
            0,
        )

        service_charge = get_numeric(
            data,
            "service_charge",
            0,
        )

        all_items_total = sum(
            get_item_total(item)
            for item in items
        )

        st.markdown(
            "### Data receipt"
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            st.write(
                "**Merchant**"
            )

            st.write(
                merchant
            )

        with col2:

            st.write(
                "**Jumlah item**"
            )

            st.write(
                len(items)
            )

        with col3:

            st.write(
                "**Grand total**"
            )

            st.write(
                format_rupiah(
                    grand_total
                )
            )

        st.markdown("---")

        # -------------------------------------------------
        # PEOPLE
        # -------------------------------------------------

        st.markdown(
            "### 👥 Siapa saja yang ikut?"
        )

        st.write(
            "Masukkan nama semua orang yang ikut "
            "membayar tagihan."
        )

        people = st.session_state.people

        people_to_delete = None

        for i in range(len(people)):

            col1, col2 = st.columns(
                [5, 1]
            )

            with col1:

                new_name = st.text_input(
                    f"Nama orang {i + 1}",
                    value=people[i],
                    key=f"person_name_{i}",
                )

                people[i] = new_name

            with col2:

                st.write("")

                if len(people) > 1:

                    if st.button(
                        "🗑️",
                        key=f"delete_person_{i}",
                    ):

                        people_to_delete = i

        if people_to_delete is not None:

            deleted_person = people.pop(
                people_to_delete
            )

            for item_index in list(
                st.session_state.assignments.keys()
            ):

                assigned = (
                    st.session_state.assignments[
                        item_index
                    ]
                )

                st.session_state.assignments[
                    item_index
                ] = [
                    person
                    for person in assigned
                    if person != deleted_person
                ]

            st.rerun()

        if st.button(
            "＋ Tambah orang",
        ):

            people.append(
                f"Orang {len(people) + 1}"
            )

            st.rerun()

        st.session_state.people = people

        # -------------------------------------------------
        # ITEM ASSIGNMENT
        # -------------------------------------------------

        st.markdown("---")

        st.markdown(
            "### 🧾 Bagikan item"
        )

        st.caption(
            "Jika satu item dimakan bersama, "
            "pilih beberapa orang. Harga item akan "
            "dibagi rata di antara mereka."
        )

        if len(items) == 0:

            st.warning(
                "Belum ada item pada receipt."
            )

        else:

            for i, item in enumerate(items):

                item_name = item.get(
                    "name",
                    f"Item {i + 1}",
                )

                item_total = get_item_total(
                    item
                )

                st.markdown(
                    '<div class="item-card">',
                    unsafe_allow_html=True,
                )

                st.markdown(
                    f"### {item_name}"
                )

                # -------------------------------------------------
                # ITEM PRICE INFORMATION
                # -------------------------------------------------

                item_display = calculate_item_display(
                    item_total=item_total,
                    all_items_total=all_items_total,
                    grand_total=grand_total,
                    tax=tax,
                    voucher=voucher,
                    service_charge=service_charge,
                )

                st.write(
                    f"**Harga item:** "
                    f"{format_rupiah(item_total)}"
                )

                # -------------------------------------------------
                # TAX INFORMATION
                # -------------------------------------------------

                if tax > 0:

                    st.write(
                        f"**PB1 / PPN tercatat:** "
                        f"{format_rupiah(tax)}"
                    )

                    st.caption(
                        "PPN/PB1 ditampilkan sebagai "
                        "informasi dari nota dan tidak "
                        "selalu ditambahkan lagi ke grand total."
                    )

                # -------------------------------------------------
                # VOUCHER
                # -------------------------------------------------

                if voucher > 0:

                    voucher_allocated = (
                        item_display[
                            "voucher_allocated"
                        ]
                    )

                    st.write(
                        f"**Alokasi voucher:** "
                        f"-{format_rupiah(voucher_allocated)}"
                    )

                # -------------------------------------------------
                # SERVICE
                # -------------------------------------------------

                if service_charge > 0:

                    service_allocated = (
                        item_display[
                            "service_allocated"
                        ]
                    )

                    st.write(
                        f"**Service charge tercatat:** "
                        f"{format_rupiah(service)}"
                    )

                # -------------------------------------------------
                # FINAL ITEM TOTAL
                # -------------------------------------------------

                final_item_total = (
                    item_display[
                        "final_total"
                    ]
                )

                st.write(
                    f"**Total item setelah "
                    f"penyesuaian:** "
                    f"**{format_rupiah(final_item_total)}**"
                )

                st.markdown("")

                # -------------------------------------------------
                # ASSIGNMENT
                # -------------------------------------------------

                previous_assignment = (
                    st.session_state.assignments.get(
                        i,
                        [],
                    )
                )

                previous_assignment = [
                    person
                    for person in previous_assignment
                    if person in people
                ]

                selected_people = st.multiselect(
                    "Dibayar oleh:",
                    options=people,
                    default=previous_assignment,
                    key=f"assignment_{i}",
                )

                st.session_state.assignments[
                    i
                ] = selected_people

                if selected_people:

                    share = (
                        final_item_total
                        / len(selected_people)
                    )

                    st.caption(
                        "Bagian per orang "
                        "(sudah termasuk penyesuaian): "
                        + format_rupiah(share)
                    )

                    st.write(
                        ", ".join(
                            selected_people
                        )
                    )

                else:

                    st.warning(
                        "Belum ada orang yang dipilih "
                        "untuk item ini."
                    )

                st.markdown(
                    "</div>",
                    unsafe_allow_html=True,
                )

        # -------------------------------------------------
        # CHECK ASSIGNMENT
        # -------------------------------------------------

        all_items_assigned = True

        for i in range(len(items)):

            if not st.session_state.assignments.get(
                i,
                [],
            ):

                all_items_assigned = False

        st.markdown("---")

        # -------------------------------------------------
        # PREVIEW SPLIT
        # -------------------------------------------------

        if (
            all_items_assigned
            and len(people) > 0
        ):

            calculation = calculate_split(
                data,
                people,
                st.session_state.assignments,
            )

            preview_totals = round_split_totals(
                calculation[
                    "person_totals"
                ],
                calculation[
                    "grand_total"
                ],
            )

            st.markdown(
                "### 💰 Preview pembagian"
            )

            preview_cols = st.columns(
                len(people)
            )

            for index, person in enumerate(
                people
            ):

                with preview_cols[index]:

                    st.metric(
                        person,
                        format_rupiah(
                            preview_totals.get(
                                person,
                                0,
                            )
                        ),
                    )

            st.caption(
                "Total seluruh bagian akan disesuaikan "
                "agar sama persis dengan grand total receipt."
            )

        else:

            st.warning(
                "Pastikan setiap item sudah memiliki "
                "minimal satu orang yang membayar."
            )

        # -------------------------------------------------
        # NAVIGATION
        # -------------------------------------------------

        col_back, col_next = st.columns(
            [1, 2]
        )

        with col_back:

            if st.button(
                "← Kembali ke Cek Data",
                use_container_width=True,
            ):

                st.session_state.step = 2

                st.rerun()

        with col_next:

            if st.button(
                "Lihat Hasil →",
                type="primary",
                use_container_width=True,
                disabled=not all_items_assigned,
            ):

                st.session_state.step = 4

                st.rerun()


# =========================================================
# STEP 4
# HASIL
# =========================================================

if st.session_state.step == 4:

    st.markdown(
        "## 4. Hasil"
    )

    data = st.session_state.receipt_data

    if data is None:

        st.warning(
            "Data receipt belum tersedia."
        )

    else:

        people = st.session_state.people

        assignments = (
            st.session_state.assignments
        )

        calculation = calculate_split(
            data,
            people,
            assignments,
        )

        final_totals = round_split_totals(
            calculation[
                "person_totals"
            ],
            calculation[
                "grand_total"
            ],
        )

        merchant = data.get(
            "merchant",
            "-",
        )

        grand_total = get_numeric(
            data,
            "grand_total",
            0,
        )

        tax = get_numeric(
            data,
            "tax",
            0,
        )

        voucher = get_numeric(
            data,
            "voucher",
            0,
        )

        st.success(
            "Pembagian tagihan berhasil dihitung."
        )

        # -------------------------------------------------
        # RECEIPT SUMMARY
        # -------------------------------------------------

        st.markdown(
            f"### 🧾 {merchant}"
        )

        col1, col2, col3 = st.columns(3)

        with col1:

            st.write(
                "**Grand total**"
            )

            st.write(
                format_rupiah(
                    grand_total
                )
            )

        with col2:

            st.write(
                "**Jumlah orang**"
            )

            st.write(
                len(people)
            )

        with col3:

            st.write(
                "**Jumlah item**"
            )

            st.write(
                len(
                    data.get(
                        "items",
                        [],
                    )
                )
            )

        st.markdown("---")

        # -------------------------------------------------
        # RECEIPT COMPONENTS
        # -------------------------------------------------

        st.markdown(
            "### 🧮 Ringkasan transaksi"
        )

        summary_col1, summary_col2, summary_col3 = st.columns(
            3
        )

        with summary_col1:

            st.write(
                "**Total item**"
            )

            st.write(
                format_rupiah(
                    calculation[
                        "all_items_total"
                    ]
                )
            )

        with summary_col2:

            if tax > 0:

                st.write(
                    "**PB1 / PPN tercatat**"
                )

                st.write(
                    format_rupiah(
                        tax
                    )
                )

            elif voucher > 0:

                st.write(
                    "**Voucher**"
                )

                st.write(
                    "-" + format_rupiah(
                        voucher
                    )
                )

            else:

                st.write(
                    "**Penyesuaian**"
                )

                adjustment = (
                    grand_total
                    - calculation[
                        "all_items_total"
                    ]
                )

                st.write(
                    format_rupiah(
                        adjustment
                    )
                )

        with summary_col3:

            st.write(
                "**Grand total**"
            )

            st.write(
                format_rupiah(
                    grand_total
                )
            )

        st.markdown("---")

        # -------------------------------------------------
        # PER PERSON
        # -------------------------------------------------

        st.markdown(
            "### 💸 Rincian pembayaran"
        )

        for person in people:

            total = final_totals.get(
                person,
                0,
            )

            st.markdown(
                '<div class="result-card">',
                unsafe_allow_html=True,
            )

            st.markdown(
                f"## 👤 {person}"
            )

            st.markdown(
                f'<div class="total-result">'
                f'{format_rupiah(total)}'
                f'</div>',
                unsafe_allow_html=True,
            )

            st.write(
                "Rincian item:"
            )

            person_items = (
                calculation[
                    "person_items"
                ].get(
                    person,
                    [],
                )
            )

            raw_item_total = sum(
                item["amount"]
                for item in person_items
            )

            for item in person_items:

                st.write(
                    f"• {item['name']} — "
                    f"{format_rupiah(item['amount'])}"
                )

            adjustment = (
                total
                - raw_item_total
            )

            if abs(adjustment) > 0.5:

                if adjustment > 0:

                    st.write(
                        f"• Pajak / biaya tambahan — "
                        f"{format_rupiah(adjustment)}"
                    )

                else:

                    st.write(
                        f"• Diskon / voucher — "
                        f"-{format_rupiah(abs(adjustment))}"
                    )

            st.markdown(
                "</div>",
                unsafe_allow_html=True,
            )

        # -------------------------------------------------
        # TOTAL CHECK
        # -------------------------------------------------

        total_result = sum(
            final_totals.values()
        )

        st.markdown("---")

        st.markdown(
            "### ✅ Cek total"
        )

        check_col1, check_col2, check_col3 = st.columns(
            3
        )

        with check_col1:

            st.metric(
                "Grand total receipt",
                format_rupiah(
                    grand_total
                ),
            )

        with check_col2:

            st.metric(
                "Total hasil split",
                format_rupiah(
                    total_result
                ),
            )

        with check_col3:

            difference = (
                total_result
                - grand_total
            )

            st.metric(
                "Selisih",
                format_rupiah(
                    difference
                ),
            )

        if difference == 0:

            st.success(
                "✓ Total pembagian sudah sama "
                "persis dengan grand total receipt."
            )

        else:

            st.warning(
                "Masih terdapat selisih pembulatan."
            )

        # -------------------------------------------------
        # NAVIGATION
        # -------------------------------------------------

        st.markdown("")

        col_back, col_restart = st.columns(
            2
        )

        with col_back:

            if st.button(
                "← Kembali ke Bagi Item",
                use_container_width=True,
            ):

                st.session_state.step = 3

                st.rerun()

        with col_restart:

            if st.button(
                "🔄 Mulai Receipt Baru",
                use_container_width=True,
            ):

                st.session_state.step = 1

                st.session_state.receipt_data = None

                st.session_state.raw_output = None

                st.session_state.uploaded_file_name = None

                st.session_state.people = [
                    "Orang 1",
                    "Orang 2",
                ]

                st.session_state.assignments = {}

                st.rerun()


# =========================================================
# FOOTER
# =========================================================

st.markdown("---")

st.caption(
    f"Model: {selected_model} • "
    f"Currency: {selected_currency}"
)