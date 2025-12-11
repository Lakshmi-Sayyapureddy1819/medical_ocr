import re
from rapidfuzz import fuzz

def _clean_number(s: str):
    if not s:
        return None
    s = s.replace("O", "0").replace("o", "0")
    s = s.replace("I", "1").replace("l", "1")
    s = re.sub(r"[^0-9]", "", s)
    return s if s else None

def extract_dates(text: str):
    # formats like 6/04/25 or 06-04-2025
    matches = re.findall(r"\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b", text)
    return list(dict.fromkeys(matches))

def extract_ipd_uhid(text: str):
    # capture groups after IPD or UHID keywords
    ipd_candidates = re.findall(r"IPD[^0-9A-Za-z\n\r:]*([0-9OIl\-\s]{3,40})", text, flags=re.IGNORECASE)
    uhid_candidates = re.findall(r"UHID[^0-9A-Za-z\n\r:]*([0-9OIl\-\s]{3,40})", text, flags=re.IGNORECASE)

    ipd = None
    uhid = None
    for c in ipd_candidates:
        cleaned = _clean_number(c)
        if cleaned and len(cleaned) >= 3:
            ipd = cleaned
            break
    for c in uhid_candidates:
        cleaned = _clean_number(c)
        if cleaned and len(cleaned) >= 3:
            uhid = cleaned
            break
    # fallback: any long number in header (first 12 lines)
    if not (ipd or uhid):
        header = "\n".join(text.splitlines()[:12])
        nums = re.findall(r"[0-9]{4,}", header)
        if nums:
            if not ipd:
                ipd = nums[0]
            if len(nums) > 1 and not uhid:
                uhid = nums[1]
    return ipd, uhid

def extract_bed(text: str):
    m = re.search(r"Bed\s*No[:\s]*([0-9OIl]+)", text, flags=re.IGNORECASE)
    if m:
        return _clean_number(m.group(1))
    return None

def extract_age(text: str):
    m = re.search(r"Age[:\s]*([0-9]{1,3})", text, flags=re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"\b([0-9]{1,3})\s*[Yy]\b", text)
    if m:
        return m.group(1)
    return None

def extract_sex(text: str):
    m = re.search(r"Sex[:\s]*([MFmf]|Male|Female)", text, flags=re.IGNORECASE)
    if m:
        return m.group(1)[0].upper()
    if re.search(r"\bMale\b", text, flags=re.IGNORECASE):
        return "M"
    if re.search(r"\bFemale\b", text, flags=re.IGNORECASE):
        return "F"
    return None

def extract_patient_name(text: str):
    # Primary: explicit "Patient Name" field
    m = re.search(r"Patient\s*Name[:\s\-]*([A-Za-z .'\-]{3,80})", text, flags=re.IGNORECASE)
    if m:
        raw = re.sub(r"[^A-Za-z '\-]", " ", m.group(1)).strip()
        parts = [p for p in raw.split() if len(p) >= 2]
        if parts:
            return " ".join(parts[:4]).title()
    # fallback: try header first 8 lines for capitalized multi-word token
    header = "\n".join(text.splitlines()[:8])
    words = re.findall(r"[A-Z][a-z]{1,}|[a-z]{3,}", header)
    if len(words) >= 2:
        # heuristic: return two most plausible adjacent words
        header_tokens = re.findall(r"[A-Za-z']{2,}", header)
        if header_tokens:
            name = " ".join(header_tokens[:3])
            return name.title()
    return None

def extract_pii_fixed(text: str):
    raw = "\n".join([l.strip() for l in text.splitlines() if l.strip()])

    patient_name = extract_patient_name(raw)
    age = extract_age(raw)
    sex = extract_sex(raw)
    ipd_no, uhid = extract_ipd_uhid(raw)
    bed_no = extract_bed(raw)
    dates = extract_dates(raw)

    # hospital name detection
    hospital = None
    for line in raw.splitlines()[:12]:
        if "institute" in line.lower() and "hospital" in line.lower():
            hospital = line.strip()
            break
    if not hospital:
        # default fallback
        hospital = "INSTITUTE OF MEDICAL SCIENCES & SUM HOSPITAL"

    return {
        "patient_name": patient_name,
        "age": age,
        "sex": sex,
        "ipd_no": ipd_no,
        "uhid": uhid,
        "bed_no": bed_no,
        "hospital_name": hospital,
        "dates": dates
    }
