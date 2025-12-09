import re
from typing import Dict, Any, List


def _pick_best_age(cands: List[str]) -> str | None:
    # prefer 2-digit ages between 10 and 100
    nums = []
    for c in cands:
        try:
            v = int(c)
            nums.append(v)
        except ValueError:
            continue
    # sort by "goodness": 2-digit & in adult range first
    nums_sorted = sorted(nums, key=lambda x: (not (10 <= x <= 100), abs(x-30)))
    return str(nums_sorted[0]) if nums_sorted else None


def extract_pii_fixed(text: str) -> Dict[str, Any]:
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    low_lines = [l.lower() for l in lines]

    pii: Dict[str, Any] = {
        "patient_name": None,
        "age": None,
        "sex": None,
        "ipd_no": None,
        "uhid": None,
        "bed_no": None,
        "hospital_name": None,
        "dates": [],
    }

    # ---------------- hospital name ----------------
    for l in low_lines[:6]:
        if "institute" in l and "hospital" in l:
            pii["hospital_name"] = l
            break

    name_candidates: List[str] = []
    age_candidates: List[str] = []
    sex_candidates: List[str] = []
    ipd_candidates: List[str] = []
    uhid_candidates: List[str] = []
    bed_candidates: List[str] = []
    date_candidates: List[str] = []

    n = len(lines)

    for i, (line, low) in enumerate(zip(lines, low_lines)):
        # -------- NAME: look at this line + following 2 lines --------
        if ("patient" in low or "paticnt" in low or "palient" in low or "pat ent" in low) and "name" in low:
            # Remove "patient ... name" prefix
            after = re.sub(r".*name[:\s-]*", "", line, flags=re.I).strip()

            tokens: List[str] = []
            if after:
                tokens.extend(after.split())

            # look ahead up to 2 lines until we hit age/sex/ipd/uhid
            j = i + 1
            while j < n and not re.search(r"\bage\b|\bsex\b|\bipd\b|\buhid\b|\bbed\b", low_lines[j]):
                tokens.extend(lines[j].split())
                j += 1

            # keep only alphabetic tokens (remove numbers / junk)
            tokens = [t for t in tokens if re.match(r"^[A-Za-z]+$", t)]
            if len(tokens) >= 2:
                name_candidates.append(" ".join(tokens[:2]))

        # -------- AGE: this line, or next line if this just says "Age;" --------
        if "age" in low:
            # digits on same line
            nums = re.findall(r"(\d{1,3})", low)
            if not nums and i + 1 < n:
                # check next line if only digits there
                nums = re.findall(r"(\d{1,3})", low_lines[i + 1])
            age_candidates.extend(nums)

        # -------- SEX: letter on same or next line --------
        if "sex" in low or "5ex" in low or "sax" in low:
            m = re.search(r"(sex|5ex|sax)[:\s-]*([mf])", low)
            if not m and i + 1 < n:
                m = re.search(r"\b([mf])\b", low_lines[i + 1])
            if m:
                sex_candidates.append(m.group(2).upper())

        # -------- IPD --------
        if "ipd" in low:
            # pick longest digit-sequence
            nums = re.findall(r"(\d{4,})", low)
            if not nums and i + 1 < n:
                nums = re.findall(r"(\d{4,})", low_lines[i + 1])
            if nums:
                ipd_candidates.append(max(nums, key=len))

        # -------- UHID --------
        if "uhid" in low:
            nums = re.findall(r"(\d{4,})", low)
            if not nums and i + 1 < n:
                nums = re.findall(r"(\d{4,})", low_lines[i + 1])
            if nums:
                uhid_candidates.append(max(nums, key=len))

        # -------- BED NO --------
        if "bed" in low:
            nums = re.findall(r"(\d{1,4})", low)
            if not nums and i + 1 < n:
                nums = re.findall(r"(\d{1,4})", low_lines[i + 1])
            if nums:
                bed_candidates.append(nums[0])

        # -------- DATES: collect all --------
        dt = re.findall(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", line)
        if dt:
            date_candidates.extend(dt)

    # pick best candidates
    if name_candidates:
        # often second occurrence is the cleanest; but pick the longest
        pii["patient_name"] = max(name_candidates, key=len)

    if age_candidates:
        pii["age"] = _pick_best_age(age_candidates)

    if sex_candidates:
        # usually just 'M' / 'F'
        pii["sex"] = sex_candidates[0]

    if ipd_candidates:
        pii["ipd_no"] = max(ipd_candidates, key=len)

    if uhid_candidates:
        pii["uhid"] = max(uhid_candidates, key=len)

    if bed_candidates:
        pii["bed_no"] = bed_candidates[0]

    if date_candidates:
        pii["dates"] = list(dict.fromkeys(date_candidates))  # unique preserve order

    return pii
