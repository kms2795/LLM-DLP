from datetime import date

def is_valid_birthdate(yy: int, mm: int, dd: int, century: int):
    """생년월일이 실제로 존재하고, 미래 날짜가 아닌지 확인"""
    try:
        birth = date(century + yy, mm, dd)
    except ValueError:
        return False
    return birth <= date.today()

def is_valid_checksum(digits: str):
    """2세대 주민번호 체크섬 검증 (3세대는 원래 안 맞는 게 정상)"""
    weights = [2, 3, 4, 5, 6, 7, 8, 9, 2, 3, 4, 5]
    total = sum(int(d) * w for d, w in zip(digits[:12], weights))
    checksum = (11 - (total % 11)) % 10
    return checksum == int(digits[12])
