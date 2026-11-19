import os
import json
import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer

from phone_detector import detect_phone_num
from rrn_detector import detect_rrn
from email_detector import detect_email
from api_key_detector import detect_api_key

# ===== NER 모델 로드 (서버 시작 시 한 번만 실행됨) =====
_NER_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ner_model_final")
_tokenizer = AutoTokenizer.from_pretrained(_NER_PATH)
_model = AutoModelForTokenClassification.from_pretrained(_NER_PATH)
_model.eval()

with open(os.path.join(_NER_PATH, "label_map.json"), encoding="utf-8") as f:
    _id2label = {int(k): v for k, v in json.load(f)["id2label"].items()}

LABEL_KOREAN = {"PER": "이름", "ADDR": "주소", "PHONE": "전화번호", "EMAIL": "이메일", "RRN": "주민번호"}

# 로그에 값을 일절 남기지 않는 유형 (법 제24조의2 / 자격증명)
_NO_EVIDENCE = {"RRN", "API_KEY"}

# 형식이 확정적이라 모델보다 우선하는 유형.
# 주민번호는 자릿수와 성별코드에 더해 날짜 유효성까지 통과해야 하고,
# API 키는 접두사가 고정이라 문맥으로 뒤집을 여지가 없습니다.
_STRICT_REGEX = {"RRN", "API_KEY"}


def ner_predict(text):
    """NER 모델로 문장을 분석해서 (시작, 끝, 라벨) 리스트 반환"""
    encoding = _tokenizer(text, return_offsets_mapping=True, return_tensors="pt")
    offsets = encoding.pop("offset_mapping")[0]

    with torch.no_grad():
        outputs = _model(**encoding)
    preds = outputs.logits.argmax(dim=2)[0]

    entities = []
    cur_label, cur_start, cur_end = None, None, None

    for idx, (s, e) in enumerate(offsets):
        s, e = s.item(), e.item()
        if s == e:
            continue
        label = _id2label[preds[idx].item()]

        if label == "O":
            if cur_label:
                entities.append((cur_start, cur_end, cur_label))
                cur_label = None
            continue

        tag, ent_type = label.split("-", 1)
        if tag == "B" or ent_type != cur_label:
            if cur_label:
                entities.append((cur_start, cur_end, cur_label))
            cur_label, cur_start, cur_end = ent_type, s, e
        else:
            cur_end = e

    if cur_label:
        entities.append((cur_start, cur_end, cur_label))

    return entities


def _find_spans(text, values, label):
    """탐지된 값들의 실제 위치를 찾아서 (시작, 끝, 라벨) 형태로 변환"""
    spans = []
    pos = 0
    for v in values:
        idx = text.find(v, pos)
        if idx == -1:
            idx = text.find(v)
        if idx != -1:
            spans.append((idx, idx + len(v), label))
            pos = idx + len(v)
    return spans


def _overlaps(a, b):
    return a[0] < b[1] and b[0] < a[1]


def _partial_mask(value: str, label: str) -> str:
    """로그에 남길 부분 마스킹본 생성 (재식별 불가 수준까지만 남김)"""
    if label == "PER":
        return value[0] + "*" * (len(value) - 1) if len(value) > 1 else "*"

    if label == "PHONE":
        digits = "".join(ch for ch in value if ch.isdigit())
        return digits[:-4] + "****" if len(digits) > 4 else "*" * len(digits)

    if label == "EMAIL":
        local = value.split("@")[0]
        head = local[:2] if len(local) >= 4 else local[:1]
        return head + "***@***"

    if label == "ADDR":
        parts = value.split()
        return " ".join(parts[:2]) + " ***" if len(parts) > 2 else value

    return "***"


def mask_text(text: str):
    """텍스트에서 민감정보 탐지 후 마스킹 처리 (정규식 + NER 하이브리드)
    return: (masked_text, detected_types, risk_level, evidence)
    """
    # 1. 정규식 결과를 위치 정보 포함 형태로 수집
    regex_spans = []
    regex_spans += _find_spans(text, [r['number'] for r in detect_rrn(text)], "RRN")
    regex_spans += _find_spans(text, [k['key'] for k in detect_api_key(text)], "API_KEY")
    regex_spans += _find_spans(text, detect_phone_num(text), "PHONE")
    regex_spans += _find_spans(text, detect_email(text), "EMAIL")

    # 2. NER 결과 수집 (PER, ADDR은 정규식이 원래 못 잡는 영역)
    ner_spans = ner_predict(text)

    # 3-1. 주민번호·API키 정규식이 잡은 구간은 무조건 우선합니다.
    #      모델이 같은 구간을 다르게 쪼개도 그 조각들을 버립니다.
    #      (구어체 문맥에서 모델이 주민번호 가운데를 PHONE으로 찍어
    #       한 개체가 세 조각으로 분절되던 문제를 막습니다)
    strict_spans = [r for r in regex_spans if r[2] in _STRICT_REGEX]
    other_regex = [r for r in regex_spans if r[2] not in _STRICT_REGEX]

    if strict_spans:
        other_regex = [r for r in other_regex
                       if not any(_overlaps(r, s) for s in strict_spans)]
        ner_spans = [n for n in ner_spans
                     if not any(_overlaps(n, s) for s in strict_spans)]

    # 3-2. 나머지 병합: 경계가 정확히 일치하면 정규식을 신뢰(형식이 명확하므로),
    #      어긋나게 겹치면 NER을 신뢰(덩어리 경계는 문맥을 봐야 알 수 있으므로)
    exact_regex = [r for r in other_regex if any(r[0] == n[0] and r[1] == n[1] for n in ner_spans)]
    filtered_regex = [r for r in other_regex if not any(_overlaps(r, n) for n in ner_spans)]
    exact_bounds = {(r[0], r[1]) for r in exact_regex}
    filtered_ner = [n for n in ner_spans if (n[0], n[1]) not in exact_bounds]
    all_spans = strict_spans + filtered_regex + exact_regex + filtered_ner

    # 4. 혹시 남은 겹침 정리 (앞쪽 우선)
    final_spans = []
    last_end = -1
    for s, e, l in sorted(all_spans, key=lambda x: x[0]):
        if s >= last_end:
            final_spans.append((s, e, l))
            last_end = e

    # 5. 라벨별 등장 순서대로 번호 매기기
    numbered = []
    counters = {}
    for s, e, l in final_spans:
        counters[l] = counters.get(l, 0) + 1
        numbered.append((s, e, l, counters[l]))

    # 6. 뒤에서부터 치환 (앞쪽 인덱스가 안 밀리도록)
    masked_text = text
    detected_types = set()
    for s, e, l, n in sorted(numbered, key=lambda x: -x[0]):
        masked_text = masked_text[:s] + f"[{l}_{n}]" + masked_text[e:]
        detected_types.add("API키" if l == "API_KEY" else LABEL_KOREAN.get(l, l))

    detected_types = list(detected_types)

    # 6-1. 로그용 증거 문자열 (주민번호·API키는 값을 남기지 않음)
    evidence_parts = []
    for s, e, l, n in numbered:
        if l in _NO_EVIDENCE:
            continue
        evidence_parts.append(f"{l}_{n}={_partial_mask(text[s:e], l)}")
    evidence = "; ".join(evidence_parts) if evidence_parts else None

    # 7. 위험도 판단
    if "주민번호" in detected_types or "API키" in detected_types:
        risk_level = "HIGH"
    elif "전화번호" in detected_types or "주소" in detected_types:
        risk_level = "MEDIUM"
    elif "이메일" in detected_types or "이름" in detected_types:
        risk_level = "LOW"
    else:
        risk_level = "NONE"

    return masked_text, detected_types, risk_level, evidence
