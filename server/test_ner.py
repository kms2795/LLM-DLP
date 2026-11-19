from transformers import AutoModelForTokenClassification, AutoTokenizer
import json, torch

MODEL_PATH = "./ner_model_final"
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
model = AutoModelForTokenClassification.from_pretrained(MODEL_PATH)

with open(f"{MODEL_PATH}/label_map.json", encoding="utf-8") as f:
    label_map = json.load(f)
    id2label = {int(k): v for k, v in label_map["id2label"].items()}

text = "김민준님의 연락처는 010-1234-5678입니다"
encoding = tokenizer(text, return_offsets_mapping=True, return_tensors="pt")
offsets = encoding.pop("offset_mapping")[0]

with torch.no_grad():
    outputs = model(**encoding)

preds = outputs.logits.argmax(dim=2)[0]

for idx, (s, e) in enumerate(offsets):
    if s == e:
        continue
    label = id2label[preds[idx].item()]
    if label != "O":
        print(f"'{text[s:e]}' -> {label}")
