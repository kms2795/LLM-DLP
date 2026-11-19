import re
from validators import is_valid_birthdate, is_valid_checksum

def detect_rrn(text: str):
    """주민등록번호/외국인등록번호 탐지: 구조 필터링 / 생년월일 유효성 검사"""
    pattern = r'\d{6}-?[1-8]\d{6}'
    candidates = re.findall(pattern, text)

    results = []
    for c in candidates:
        digits = c.replace('-', '')
        yy = int(digits[0:2])
        mm = int(digits[2:4])
        dd = int(digits[4:6])
        gender_digit = int(digits[6])

        century = 1900 if gender_digit in (1,2,5,6) else 2000

        if is_valid_birthdate(yy, mm, dd, century):
            results.append({
                "number": c,
                "checksum_valid": is_valid_checksum(digits)
            })
    return results
