## 개요

ChatGPT·Claude 같은 생성형 AI에 입력한 문장은 전송 버튼을 누르는 순간 외부
서버로 나갑니다. 기존 DLP는 파일 첨부와 메일 발송을 전제로 설계되어 브라우저
입력창을 보지 못하고, 사후 로그 분석으로는 이미 나간 정보를 되돌릴 수 없습니다.

이 프로젝트는 개입 지점을 **전송 직전**으로 옮깁니다. 크롬 확장 프로그램이 전송
동작을 가로채 문장을 탐지 서버로 보내고, 서버는 이름·주소·전화번호·이메일·
주민등록번호·API 키를 찾아 유형 표시로 치환한 문장을 돌려줍니다. 위험도가 높은
항목은 전송 자체를 중단합니다.

한국어가 까다로운 지점은 이름과 주소입니다. 형식이 고정된 번호는 정규식으로
잡히지만 "김민성"과 "김치는"을 구분하려면 문맥이 필요합니다. 그래서 정규식과
klue/bert-base를 미세조정한 개체명 인식 모델을 함께 쓰고, 두 결과를 3단계
규칙으로 병합합니다.

탐지 기록에는 입력 원문을 저장하지 않습니다. 보호 장치가 그 자체로 감시 도구가
되지 않도록, 유형과 위험도, 부분 마스킹한 값만 남깁니다. 주민등록번호와 API 키는
부분 형태로도 기록하지 않습니다.

### 성능

| 방식 | 학습 형식 | 미학습 값 |
|---|---|---|
| 정규식 단독 | 0.390 | 0.481 |
| NER 단독 | 1.000 | 1.000 |
| 하이브리드 | 1.000 | 0.987 |

직접 작성한 구어체 문장(학습 분포 밖)에서는 F1 0.806입니다. 학습·평가 데이터가
모두 합성이라는 점이 이 수치의 한계이며, 실제 사용 환경의 성능은 더 낮을 수
있습니다.

### 한계

- 학습 데이터가 합성 데이터입니다. 실제 개인정보 수집은 이 작품이 막으려는 행위라 선택지가 없었습니다
- 클라이언트와 서버 사이 통신이 아직 평문입니다 (HTTPS 미적용)
- 서버가 1대라 중단되면 전체 탐지가 멈춥니다
- 텍스트 입력만 다룹니다. 파일 첨부와 이미지 붙여넣기는 범위 밖입니다


 -------------------------------------------------------------------------------

 ## Overview

Anything typed into ChatGPT or Claude leaves the browser the moment you hit send.
Conventional DLP was built around file attachments and outbound mail, so it never
sees the prompt box — and analyzing logs afterward cannot recall what has already
been sent.

This project moves the control point to **just before transmission**. A Chrome
extension intercepts the send action, passes the text to a detection server, and
receives it back with names, addresses, phone numbers, emails, resident
registration numbers, and API keys replaced by type placeholders. High-risk items
block the send outright.

Names and addresses are the hard part in Korean. Fixed-format numbers fall to
regular expressions, but telling the surname 김 in "김민성" from the same syllable
in "김치" requires context. The system therefore pairs regex detectors with a
token-classification model fine-tuned from klue/bert-base, merging the two through
a three-stage rule.

Detection logs never store the original text. So that a safeguard does not itself
become surveillance, only the entity type, risk level, and a partially masked value
are kept — and resident registration numbers and API keys are not recorded even in
partial form.

### Results

| Method | In-distribution | Unseen values |
|---|---|---|
| Regex only | 0.390 | 0.481 |
| NER only | 1.000 | 1.000 |
| Hybrid | 1.000 | 0.987 |

On hand-written colloquial sentences outside the training distribution, F1 drops to
0.806. Both training and evaluation data are synthetic, which bounds how much these
numbers say about real-world use.

### Known limitations

- Trained on synthetic data — collecting real PII is precisely what this tool exists to prevent
- Client–server traffic is not yet encrypted (no HTTPS)
- A single server instance; detection stops entirely if it goes down
- Text input only — file uploads and pasted images are out of scope
