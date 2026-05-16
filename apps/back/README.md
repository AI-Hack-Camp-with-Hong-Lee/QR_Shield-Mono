# QR Shield Back

FastAPI 기반 URL 위험도 분석 API입니다. 현재 버전은 LLM 서버 없이 룰 기반으로 위험 점수, 등급, 설명, 행동 가이드를 반환합니다.

## 실행

```bash
cd apps/back
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Docker 실행

루트 디렉터리에서 실행합니다.

```bash
docker compose up --build back
```

백엔드는 `http://localhost:8000`에서 실행됩니다.

## LLM 서버 연동 준비

기본값은 LLM 연동 비활성화입니다. LLM 서버가 없어도 룰 기반 분석은 계속 동작합니다.

LLM 서버를 함께 사용할 때는 백엔드 환경 변수에 아래 값을 설정합니다.

```bash
QR_SHIELD_LLM_ENABLED=true
QR_SHIELD_LLM_BASE_URL=http://localhost:8001
QR_SHIELD_LLM_TIMEOUT_SECONDS=3.0
QR_SHIELD_LLM_ML_SCORE_WEIGHT=0.4
```

백엔드는 분석 시 아래 순서로 동작합니다.

1. 내부 룰 엔진으로 기본 신호와 점수를 계산합니다.
2. LLM 서버 `POST /api/agent/score`를 호출해 ML 점수와 리다이렉트 신호를 가져옵니다.
3. `rule_score + redirect_score + ml_score * QR_SHIELD_LLM_ML_SCORE_WEIGHT`로 최종 점수를 계산합니다.
4. LLM 서버 `POST /api/agent/explain`을 호출해 설명과 행동 가이드를 받아옵니다.
5. LLM 호출 실패 시 기존 룰 기반 설명으로 fallback합니다.

## API

### `GET /health`

서버 상태를 확인합니다.

### `POST /api/v1/analyze`

요청:

```json
{
  "url": "https://example.com"
}
```

응답:

```json
{
  "id": "8af58a1b-c5fe-449a-9bbd-456c8f4f35f3",
  "url": "https://example.com",
  "riskLevel": "safe",
  "score": 0,
  "explanation": "이 URL은 현재 룰 기반 검사에서 뚜렷한 위험 신호가 감지되지 않았습니다.",
  "actionGuide": "공식 출처에서 받은 QR 코드라면 접속해도 됩니다. 그래도 개인정보 입력 전 주소를 한 번 더 확인하세요.",
  "signals": [],
  "scannedAt": "2026-05-16T12:00:00.000000Z"
}
```

`url`에 스킴이 없으면 `https://`를 붙여 분석합니다.

## 테스트

```bash
cd apps/back
pytest
```
