import re

API_KEY_PATTERNS = {
    "OpenAI": r'sk-proj-[a-zA-Z0-9_-]{20,}|sk-[a-zA-Z0-9]{20}T3BlbkFJ[a-zA-Z0-9]{20}',
    "Anthropic": r'sk-ant-[a-zA-Z0-9_-]{20,}',
    "AWS": r'AKIA[0-9A-Z]{16}',
    "GitHub": r'ghp_[0-9a-zA-Z]{36}',
    "Google": r'AIza[0-9A-Za-z_-]{35}',
    "Slack": r'xox[baprs]-[0-9a-zA-Z-]{10,48}',
}

def detect_api_key(text: str):
    """여러 서비스의 API 키 탐지: 어떤 서비스 키인지 함께 반환"""
    results = []
    for service, pattern in API_KEY_PATTERNS.items():
        matches = re.findall(pattern, text)
        for m in matches:
            results.append({"service": service, "key": m})
    return results
