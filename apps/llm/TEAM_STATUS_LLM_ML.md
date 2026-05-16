# QR Shield — LLM·ML 담당 진행 보고서

| 항목 | 내용 |
|------|------|
| 담당 | LLM·ML (홍혜원) |
| 서비스 | `apps/llm` (FastAPI) |
| 작성 기준일 | 2026-05-16 |
| 대상 독자 | 백엔드, 프론트, PM, 전체 팀 |

---

## 1. 요약 (Executive Summary)

LLM·ML 서버는 **URL 기반 피싱 추정(ONNX)**, **HEAD 리다이렉트 분석**, **Gemini 기반 설명·행동 가이드**까지 **단독 실행·Swagger 테스트 가능**한 수준까지 구현되었다.

**최종 위험 점수·등급(안전/주의/위험)은 백엔드 책임**이며, LLM 서버는 **중간 분석 결과(`score`)**와 **설명 생성(`explain`)**만 제공한다.

**앱 End-to-End(스캔 → 결과 화면)** 는 백·프론트 연동 코드가 반영되었다. 해커톤 시 **LLM(8001)·백(8000) 동시 가동** 및 `EXPO_PUBLIC_API_URL` 설정이 필요하다.

---

## 2. 아키텍처 (팀 합의안)

```
[모바일 앱]  QR 스캔 → URL 추출
      │
      ▼
[백엔드]  POST /analyze
      │     ├─ 규칙 엔진 (risk_engine) → rule_score, signals
      │     ├─ POST LLM /api/agent/score      → ML + 리다이렉트
      │     ├─ 최종 score / level 합산        ← 백 구현
      │     └─ POST LLM /api/agent/explain  → explanation, action_guide
      ▼
[앱]  결과 화면
```

| 구분 | 담당 | 비고 |
|------|------|------|
| QR 스캔·UI | 프론트 | 현재 mock 분석 → 백 연동 필요 |
| 규칙·최종 점수·LLM 호출 | 백 | `score`→합산→`explain` 구현 |
| ML·리다이렉트·설명 API | LLM (`apps/llm`) | 구현 완료 |

---

## 3. 현재 완료 항목 (LLM·ML)

### 3.1 API

| Method | Path | 상태 | 설명 |
|--------|------|------|------|
| GET | `/api/health` | ✅ | 서버·Gemini 키 설정 여부 |
| POST | `/api/agent/score` | ✅ | 백 연동용 **중간 패키지** (최종 등급 없음) |
| POST | `/api/agent/explain` | ✅ | 백 최종 점수·등급 기반 **설명·가이드** |
| POST | `/api/agent/analyze` | ⚠️ | **로컬 테스트용**(deprecated), 통합 응답 |

### 3.2 ML (ONNX)

| 항목 | 내용 |
|------|------|
| 모델 | Hugging Face `pirocheto/phishing-url-detection` |
| 출력 | 피싱 추정 **0~100** (`ml_score`) |
| 화이트리스트 | `.go.kr`, `.or.kr`, `.ac.kr`, `.edu.kr`, `.re.kr`, `.mil.kr` → **0.0** |
| 실패 시 | `ml_available: false`, `ml_score: null` |

### 3.3 리다이렉트 (동적 분석)

| 항목 | 내용 |
|------|------|
| 방식 | `httpx` **HEAD** 요청, 수동 Location 추적 |
| 제한 | 최대 5홉, 타임아웃 3초 |
| 산출 | `final_url`, `hop_count`, `risk_factors[]`, `redirect_score` |
| 신호 유형 | `short_url`, `redirect`, `excessive_redirect`, `domain_changed`, `suspicious_tld`, `ml_high_risk` |

### 3.4 LLM (Gemini)

| 항목 | 내용 |
|------|------|
| 모델 | `gemini-2.5-flash-lite` (`.env`의 `GEMINI_MODEL`) |
| 역할 | **해설·행동 가이드만** (판정 주체 아님) |
| 실패 시 | `used_llm: false` + 등급별 템플릿 문구 |

### 3.5 문서·저장소

| 문서 | 경로 |
|------|------|
| 백엔드 연동·curl·시연 URL | `apps/llm/BACKEND_HANDOFF.md` |
| 소스 | `main` 브랜치에 `apps/llm` 포함 (머지 완료) |

### 3.6 로컬 실행

```powershell
cd apps\llm
# venv 활성화 후
pip install -r requirements.txt
# apps\llm\.env → GEMINI_API_KEY 설정
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

- Swagger: `http://127.0.0.1:8001/docs`

---

## 4. 미완료·타 팀 의존 항목

| 항목 | 상태 | 담당 |
|------|------|------|
| 백 → LLM `score` / `explain` 호출 | ✅ 구현 | `apps/back` |
| 백 최종 점수·등급 합산 | ✅ 구현 | `score_aggregator.py` |
| 프론트 → 백 `/analyze` (mock 제거) | ✅ 구현 | `EXPO_PUBLIC_API_URL` |
| 앱 E2E 시연 | ⚠️ 3서버 가동 후 검증 | 공동 |
| Docker Compose / LLM 컨테이너 | ❌ | **백·인프라 담당** (LLM은 로컬 `8001` 권장) |

---

## 5. MVP 대비 — LLM·ML 담당 범위

### 5.1 충족

- ONNX URL 피싱 확률
- HEAD 리다이렉트 추적
- 위험 신호 구조화 (`risk_factors`)
- 생성형 AI 설명·대응 가이드
- API 실패 fallback
- 백 연동용 중간 API (`/api/agent/score`)

### 5.2 LLM·ML 담당으로 남은 갭 (MVP 문서 대비)

| # | 항목 | 우선순위 | 비고 |
|---|------|----------|------|
| 1 | 백 연동 E2E 검증 | **필수** | 3서버 동시 실행 후 curl/앱 확인 |
| 2 | 팀 공유용 **고정 LLM Base URL** | **필수** | 동일 Wi-Fi IP 또는 ngrok |
| 3 | 시연 URL 3종 리허설 | **필수** | 안전 / 단축·리다이렉트 / 고위험 |
| 4 | 백 합의 스키마 ↔ 코드 필드명 일치 | **필수** | 불일치 시 `schemas/score.py` 수정 |
| 5 | explain 품질 점검 (빈 `risk_factors` + 고 ML) | 권장 | 프롬프트 보완 |
| 6 | Safety 검수(과장 표현) 2단계 | 선택 | MVP 문서 에이전트 |
| 7 | HEAD 실패 시 URL 텍스트 보완 필드 | 선택 | MVP §10 |

### 5.3 LLM·ML 담당 **아님** (백·프론트)

- HTTPS·login·APK 등 전체 규칙 표 (`risk_engine`)
- `GET /api/samples`, non_url QR 처리
- 앱 UI·QR 스캔
- 악성 URL DB / PhishTank 연동

---

## 6. LLM·ML 담당 — 남은 할 일 (체크리스트)

### Phase A — 오늘 필수 (연동·시연)

| # | 작업 | 완료 기준 |
|---|------|-----------|
| A1 | LLM 서버 상시 가동 (`0.0.0.0:8001`) | 팀원 curl `/api/health` 성공 |
| A2 | 팀 채팅에 **Base URL** 공지 | Wi-Fi IP 또는 ngrok (운영) |
| A3 | `BACKEND_HANDOFF.md` 공유 | ✅ 문서 작성 |
| A4 | 백 연동 지원 (필드·타임아웃·오류) | ✅ 백 코드 반영 |
| A5 | 시연 URL 3종 테스트·스크린샷 | `BACKEND_HANDOFF.md` 시연 URL 절 |

### Phase B — MVP 품질 (시간 있을 때)

| # | 작업 | 완료 기준 |
|---|------|-----------|
| B1 | `explain` 3 URL 수동 검수 | `BACKEND_HANDOFF.md` 시연 URL로 Swagger 검수 |
| B2 | 합의 스키마와 OpenAPI(`/docs`) 일치 확인 | `BACKEND_HANDOFF.md` |
| B3 | (선택) curl 백엔드용 | ✅ `BACKEND_HANDOFF.md` |

### Phase C — 선택 (시간 남을 때)

| # | 작업 |
|---|------|
| C1 | explain Safety 2단계 | ✅ `prompts/safety.py` |
| C2 | Docker `llm` 서비스 compose 추가 | 백·인프라 담당 (LLM Dockerfile 없음) |
| C3 | 단위 테스트 (`middle_score`, redirect) | ✅ `apps/llm/tests/` |

---

## 7. 백엔드 팀 전달 요약

**Base URL (예시):** `http://<LLM담당자_IP>:8001`  
**상세 스펙:** `apps/llm/BACKEND_HANDOFF.md`

**호출 순서**

1. `POST /api/agent/score` — `{"url":"..."}`  
2. 백에서 `final_score`, `level` 계산  
3. `POST /api/agent/explain` — `score`, `level`, `risk_factors`, `final_url`, `hop_count`, `ml_phishing_probability_percent`  
4. `action_guide`는 `string[]` → 앱용 `actionGuide`에 `"\n".join()` 필요  

**호출 금지:** `POST /api/agent/analyze` (LLM 내부 테스트용)

---

## 8. 프론트 팀 전달 요약

- 분석 API는 **백 `POST /analyze`만** 호출 (LLM 직접 호출 불필요).
- 현재 `apps/front/src/services/api.ts`는 **mock** → 백 URL로 교체 필요.

---

## 9. 리스크·대응

| 리스크 | 대응 |
|--------|------|
| LLM 서버가 담당자 PC에만 존재 | 해커톤 중 서버 유지 + IP/ngrok 공유 |
| 첫 `score` 요청 지연 (ONNX 다운로드) | 시연 전 1회 워밍업 호출 |
| 백 연동 지연 | 플랜 B: `/docs`에서 `score`+`explain` 시연, 또는 deprecated `analyze` |
| Gemini 키 미설정 | `used_llm: false`, 템플릿 설명 (동작은 유지) |

---

## 10. 연락·문의

- LLM·ML API·스키마·서버 가동: **LLM 담당**
- 백 `/analyze`·규칙·합산: **백엔드 담당**
- 앱 연동: **프론트 담당**

---

## 부록 — 주요 파일

| 파일 | 역할 |
|------|------|
| `app/api/explain_router.py` | API 라우트 |
| `app/services/middle_score.py` | ML + 리다이렉트 조립 |
| `app/ml/model.py` | ONNX |
| `app/ml/redirect.py` | HEAD 추적 |
| `app/services/gemini_service.py` | Gemini |
| `app/schemas/score.py` | ScoreRequest/Response |
| `app/schemas/explain.py` | ExplainRequest/Response |
