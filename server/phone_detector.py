import re

def detect_phone_num(text: str):
    """휴대폰 번호 탐지: 010(4-4자리) + 011~019 (3-4자리, 구번호)"""
    pattern = r'010-?\d{4}-?\d{4}|01[16789]-?\d{3,4}-?\d{4}'
    matches = re.findall(pattern, text)
    return matches
