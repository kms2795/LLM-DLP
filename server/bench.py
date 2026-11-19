import time
from masking import mask_text

cases = {
    "짧은 문장": "김민준 010-1234-5678",
    "보통 문장": "김민준님 연락처는 010-1234-5678이고 주민번호는 901231-1234567입니다",
    "긴 문장": (
        "안녕하세요 김민준입니다. 연락처는 010-1234-5678이고 "
        "주소는 서울특별시 강남구 테헤란로 152입니다. "
        "이메일은 abc@naver.com으로 보내주세요. 확인 부탁드립니다."
    ),
}

mask_text("워밍업")  # 첫 호출은 항상 느리므로 측정에서 제외

for name, text in cases.items():
    times = []
    for _ in range(5):
        t0 = time.perf_counter()
        mask_text(text)
        times.append((time.perf_counter() - t0) * 1000)
    avg = sum(times) / len(times)
    print(f"{name}  {len(text)}자  평균 {avg:.0f}ms  최소 {min(times):.0f}  최대 {max(times):.0f}")
