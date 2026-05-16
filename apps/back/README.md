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
