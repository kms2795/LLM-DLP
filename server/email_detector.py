import re

def detect_email(text: str):
    """이메일 탐지: user@domain.com 형식"""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    matches = re.findall(pattern, text)
    return matches
