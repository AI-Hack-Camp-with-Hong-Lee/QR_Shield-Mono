# QR Shield Monorepo Structure

QR Shield는 QR을 스캔한 뒤 URL 위험도를 분석하고, 사용자가 이해하기 쉬운 설명과 행동 가이드를 제공하는 서비스입니다.

## 전체 구조

```text
QR_Shield-Mono/
  apps/
    front/
      src/
        assets/
        components/
        navigation/
        screens/
        services/
        store/
        types/
    back/
      app/
        api/
        core/
        models/
        repositories/
        schemas/
        services/
      tests/
    llm/
      app/
        api/
        core/
        prompts/
        schemas/
        services/
      tests/
  packages/
    contracts/
  docs/
    STRUCTURE.md
  infra/
    scripts/
```

## `apps/front`

React Native 기반 모바일 앱입니다.

사용자가 QR을 스캔하고, 분석 결과를 확인하는 클라이언트 영역입니다.

```text
apps/front/
  src/
    assets/
    components/
    navigation/
    screens/
    services/
    store/
    types/
```

| 경로 | 역할 |
|---|---|
| `src/assets` | 이미지, 아이콘, 폰트 등 앱 정적 리소스 |
| `src/components` | 여러 화면에서 재사용하는 UI 컴포넌트 |
| `src/navigation` | React Navigation 라우팅, 탭/스택 구조 |
| `src/screens` | QR 스캔, 분석 결과, 스캔 이력 등 화면 단위 코드 |
| `src/services` | 백엔드 API 호출, 카메라/QR 스캔 연동 로직 |
| `src/store` | 앱 전역 상태 관리 |
| `src/types` | 프론트에서 사용하는 TypeScript 타입 |

## `apps/back`

Python 기반 백엔드 API 서버입니다.

QR에서 추출된 URL을 입력받아 위험 신호를 분석하고 점수/등급을 계산합니다. 이후 LLM 서버에 설명 생성을 요청합니다.

```text
apps/back/
  app/
    api/
    core/
    models/
    repositories/
    schemas/
    services/
  tests/
```

| 경로 | 역할 |
|---|---|
| `app/api` | REST API 라우터, 엔드포인트 정의 |
| `app/core` | 환경 설정, 공통 설정, 보안/로깅 등 핵심 설정 |
| `app/models` | DB 모델 또는 도메인 모델 |
| `app/repositories` | DB 접근, 외부 데이터 저장소 접근 계층 |
| `app/schemas` | 요청/응답 DTO, API 스키마 |
| `app/services` | URL 파싱, 위험 점수 계산, 규칙 엔진, LLM 호출 로직 |
| `tests` | 백엔드 단위 테스트 및 API 테스트 |

## `apps/llm`

Python 기반 LLM/AI 설명 서버입니다.

백엔드가 계산한 위험 등급, 점수, 탐지 신호를 받아 사용자가 이해하기 쉬운 한국어 설명과 행동 가이드를 생성합니다.

```text
apps/llm/
  app/
    api/
    core/
    prompts/
    schemas/
    services/
  tests/
```

| 경로 | 역할 |
|---|---|
| `app/api` | 설명 생성 API 엔드포인트 |
| `app/core` | LLM API 키, 모델명, 공통 설정 |
| `app/prompts` | 위험 등급별 프롬프트 템플릿 |
| `app/schemas` | LLM 서버 요청/응답 스키마 |
| `app/services` | LLM 호출, 프롬프트 조립, 응답 후처리 |
| `tests` | 프롬프트/응답 포맷/서비스 테스트 |

## `packages/contracts`

앱 사이에서 공유하는 API 계약을 두는 영역입니다.

예시:

- OpenAPI 문서
- 공통 요청/응답 JSON 예시
- 위험 등급 enum 정의 문서
- front/back/llm 간 데이터 흐름 문서

## `docs`

프로젝트 문서를 관리합니다.

예시:

- 구조 설명
- API 명세
- 개발 규칙
- 발표 자료 기반 제품 설명
- 기능 요구사항

## `infra`

개발/배포 인프라 관련 파일을 두는 영역입니다.

예시:

- Docker Compose
- 배포 스크립트
- 환경 변수 템플릿
- CI/CD 설정 보조 스크립트

## 기본 데이터 흐름

```text
front
  -> QR 스캔
  -> URL 추출
  -> back 분석 API 호출

back
  -> URL 파싱
  -> 위험 신호 탐지
  -> 위험 점수/등급 계산
  -> llm 설명 API 호출

llm
  -> 위험 신호 기반 설명 생성
  -> 행동 가이드 생성

front
  -> 안전/주의/위험 결과 표시
```

