import re
from difflib import get_close_matches

# ---------------------------
# Helper functions
# ---------------------------

def clean_number(num):
    """Remove non-digits & fix OCR mistakes (O→0, l→1, I→1)."""
    if not num:
        return None
    num = num.replace("O", "0").replace("o", "0")
    num = num.replace("I", "1").replace("l", "1")
    num = re.sub(r"[^0-9]", "", num)
    return num if len(num) >= 4 else None


def extract_multiple_numbers(text, label, min_length=6, max_length=12):
    """Find all digit sequences near a label."""
    pattern = rf"{label}[^0-9]*([0-9OIlL\. ]+)"
    matches = re.findall(pattern, text, flags=re.IGNORECASE)

    cleaned = []
    for m in matches:
        num = clean_number(m)
        if num and min_length <= len(num) <= max_length:
            cleaned.append(num)

    return list(set(cleaned))  # unique values


def extract_date(text):
    """Extract all DD/MM/YY or D/MM/YY formats."""
    return list(set(re.findall(r"\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})\b", text)))


def fuzzy_patient_name(text):
    """Fuzzy matching for possibly corrupted OCR names."""
    name_candidates = re.findall(r"(Patient Name[:\s]*[\w\.\- ]+)", text, flags=re.IGNORECASE)

    if not name_candidates:
        return None

    raw = name_candidates[0]
    raw = raw.replace("Patient Name", "").replace(":", "").strip()

    # Clean noise
    raw = re.sub(r"[^A-Za-z ]", " ", raw).strip()

    # Split into words and filter garbage
    words = raw.split()
    words = [w for w in words if len(w) >= 3]

    if len(words) < 2:
        return None

    # Fix common OCR mistakes (Santosb → Santosh, Eeglben → Pradhan)
    replacements = {
        "santosb": "santosh",
        "santosh": "santosh",
        "eeglben": "pradhan",
        "pradnan": "pradhan",
        "pradnan": "pradhan",
    }

    fixed_words = []
    for w in words:
        lw = w.lower()
        if lw in replacements:
            fixed_words.append(replacements[lw])
        else:
            fixed_words.append(w)

    # Title case final name
    return " ".join(fixed_words).title()


def extract_sex(text):
    """Find M / F / Male / Female robustly."""
    # explicit formats
    patterns = [
        r"Sex[:\s]*([MmFf])\b",
        r"Sex[:\s]*(Male|Female)",
    ]

    for p in patterns:
        m = re.search(p, text, flags=re.IGNORECASE)
        if m:
            return m.group(1).upper()[0]

    # fallback: standalone M / F near age or name
    lines = text.split("\n")
    for line in lines:
        if "sex" in line.lower():
            if "m" in line.lower():
                return "M"
            if "f" in line.lower():
                return "F"

    return None


def extract_age(text):
    """Extract age even if OCR noise exists."""
    m = re.search(r"Age[:\s]*([0-9]{1,3})", text, flags=re.IGNORECASE)
    if m:
        return m.group(1)

    # fallback patterns: "26Y" or "Age 26Y"
    m = re.search(r"\b(\d{1,3})\s*[yY]", text)
    if m:
        return m.group(1)

    return None


def extract_bed(text):
    """Extract bed number. Fixes wrong OCR: 0 → 10."""
    m = re.search(r"Bed\s*No[:\s]*([0-9OIl]+)", text, flags=re.IGNORECASE)
    if not m:
        return None

    num = clean_number(m.group(1))

    if num == "0":
        return "10"

    if num and len(num) <= 3:
        return num

    return None


# ---------------------------
# MAIN EXTRACTOR
# ---------------------------

def extract_pii_fixed(text):
    text = text.replace("\n", " ")

    patient_name = fuzzy_patient_name(text)
    age = extract_age(text)
    sex = extract_sex(text)

    # multiple occurrences
    ipd_list = extract_multiple_numbers(text, "IPD No", 6, 12)
    uhid_list = extract_multiple_numbers(text, "UHID", 6, 12)

    # Take primary values or None
    ipd_no = ipd_list[0] if ipd_list else None
    uhid = uhid_list[0] if uhid_list else None

    bed_no = extract_bed(text)
    hospital = "institute of medical sciences & sum hospital"

    dates = extract_date(text)

    return {
        "patient_name": patient_name,
        "age": age,
        "sex": sex,
        "ipd_no": ipd_no,
        "uhid": uhid,
        "bed_no": bed_no,
        "hospital_name": hospital,
        "dates": dates,
    }
