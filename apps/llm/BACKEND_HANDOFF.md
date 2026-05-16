# LLM 서버 — 백엔드 연동 스펙

## Base URL

| 환경 | URL 예시 |
|------|----------|
| 로컬 (백이 호스트) | `http://127.0.0.1:8001` |
| 백이 Docker, LLM은 호스트 | `http://host.docker.internal:8001` (Windows/Mac) |
| 해커톤 Wi-Fi | `http://<LLM_PC_IP>:8001` |

헬스: `GET /api/health`

---

## 호출 순서 (필수)

1. `POST /api/agent/score` — URL만 전달 → ML + 리다이렉트 **중간 패키지**
2. **백**에서 `rule_score`와 합산 → `final_score`, `level`
3. `POST /api/agent/explain` — 최종 점수·등급·`risk_factors` 전달 → 설명·가이드
4. 앱 응답: `action_guide: string[]` → `actionGuide`에 `"\n".join()`

**호출 금지:** `POST /api/agent/analyze` (로컬 통합 테스트용, deprecated)

---

## 1. POST /api/agent/score

**Request**

```json
{ "url": "https://bit.ly/example" }
```

**Response** (최종 `total_score` / `level` 없음)

| 필드 | 타입 | 설명 |
|------|------|------|
| `url` | string | 요청 URL |
| `final_url` | string | HEAD 추적 후 최종 URL |
| `hop_count` | int | 리다이렉트 횟수 |
| `ml_score` | float \| null | ONNX 0~100, 실패 시 null |
| `ml_available` | bool | ONNX 성공 여부 |
| `redirect_score` | int | 리다이렉트 규칙 가산 합 |
| `risk_factors` | array | `{ type, description, score? }` |
| `domain_changed` | bool | |
| `is_short_url` | bool | |
| `suspicious_tld` | bool | |

---

## 2. 백 최종 점수 합산 (구현됨: `apps/back`)

```
final_score = min(rule_score + min(int(ml_score or 0) + redirect_score, 100), 100)
```

| level | 조건 |
|-------|------|
| `danger` | score ≥ 70 |
| `caution` | score ≥ 40 |
| `safe` | 그 외 |

---

## 3. POST /api/agent/explain

**Request** (핵심 필드)

```json
{
  "url": "https://bit.ly/example",
  "normalized_url": "https://bit.ly/example",
  "final_url": "https://example.org/...",
  "hop_count": 2,
  "score": 72,
  "level": "danger",
  "grade_display": "위험",
  "ml_phishing_probability_percent": 88.5,
  "risk_factors": [
    { "type": "short_url", "description": "단축 URL", "score": 20 }
  ]
}
```

**Response**

```json
{
  "explanation": "...",
  "action_guide": ["...", "..."],
  "used_llm": true,
  "model": "gemini-2.5-flash-lite"
}
```

---

## 백 환경 변수

`apps/back/.env`:

```
QR_SHIELD_LLM_BASE_URL=http://127.0.0.1:8001
QR_SHIELD_LLM_ENABLED=true
QR_SHIELD_LLM_TIMEOUT_SECONDS=60
```

LLM 미가동 시: 규칙 엔진만으로 응답 (기존 fallback 문구).

---

## 앱 계약 (`ScanResultResponse`)

| 백 필드 | 앱 필드 |
|---------|---------|
| `riskLevel` | `riskLevel` |
| `actionGuide` | `actionGuide` (문자열, 줄바꿈 join) |
| `signals` | `signals` |

엔드포인트: `POST /api/v1/analyze`

---

## curl 빠른 테스트

LLM 서버가 `http://127.0.0.1:8001` 에 떠 있다고 가정합니다.

```bash
# 헬스
curl -s http://127.0.0.1:8001/api/health

# 중간 점수
curl -s -X POST http://127.0.0.1:8001/api/agent/score \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"https://science.go.kr\"}"

# 설명 (score/level은 백이 계산한 값으로 교체)
curl -s -X POST http://127.0.0.1:8001/api/agent/explain \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"https://bit.ly/test\",\"score\":80,\"level\":\"danger\",\"risk_factors\":[]}"
```

통합 E2E (백 + LLM):

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"https://science.go.kr\"}"
```

---

## 시연용 URL 3종

| # | URL | 기대 |
|---|-----|------|
| 1 | `https://science.go.kr` | 안전·낮은 ML (화이트리스트) |
| 2 | `https://bit.ly/test` | 주의~위험, 단축·리다이렉트 `risk_factors` |
| 3 | `https://dbs-form.info/` | ML 높음 (`ml_high_risk` 가능) |

확인 순서: LLM `score` → 백 `/api/v1/analyze` → 앱 QR 스캔.

시연 전 ONNX 워밍업:

```bash
curl -s -X POST http://127.0.0.1:8001/api/agent/score \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"https://example.com\"}"
```
