import { NativeModules, Platform } from 'react-native';
import type { RiskLevel, ScanResult } from '../types';

const MOCK_RESPONSES: Record<RiskLevel, Omit<ScanResult, 'id' | 'url' | 'scannedAt'>> = {
  safe: {
    riskLevel: 'safe',
    score: 12,
    explanation: '이 URL은 안전한 것으로 분석되었습니다. 알려진 위험 신호가 감지되지 않았으며, 신뢰할 수 있는 도메인으로 확인됩니다.',
    actionGuide: '안심하고 접속하셔도 됩니다.',
    signals: [],
  },
  caution: {
    riskLevel: 'caution',
    score: 55,
    explanation: '이 URL에서 일부 주의가 필요한 신호가 감지되었습니다. 단축 URL 또는 최근 등록된 도메인일 수 있습니다.',
    actionGuide: '접속 전 URL을 직접 확인하고, 개인정보 입력에 주의하세요.',
    signals: ['단축 URL 사용', '최근 도메인 등록'],
  },
  danger: {
    riskLevel: 'danger',
    score: 88,
    explanation: '이 URL은 피싱 또는 악성코드 배포에 사용되는 패턴이 다수 감지되었습니다. 접속 시 개인정보 탈취 위험이 있습니다.',
    actionGuide: '절대 접속하지 마세요. 이 QR 코드를 공유하거나 다른 사람에게 보여주지 마세요.',
    signals: ['알려진 피싱 패턴', '의심스러운 파라미터', 'IP 직접 접근'],
  },
};

function classifyUrl(url: string): RiskLevel {
  const lower = url.toLowerCase();
  if (lower.includes('phishing') || lower.includes('malware') || lower.includes('hack') || lower.includes('evil')) {
    return 'danger';
  }
  if (lower.includes('bit.ly') || lower.includes('tinyurl') || lower.includes('unknown')) {
    return 'caution';
  }
  return 'safe';
}

async function mockAnalyzeUrl(url: string): Promise<ScanResult> {
  await new Promise((r) => setTimeout(r, 1500));

  const riskLevel = classifyUrl(url);
  const mock = MOCK_RESPONSES[riskLevel];

  return {
    id: `${Date.now()}`,
    url,
    scannedAt: new Date(),
    ...mock,
  };
}

function getExpoHost(): string | undefined {
  const scriptURL = NativeModules.SourceCode?.scriptURL as string | undefined;
  const match = scriptURL?.match(/^(?:https?|exp):\/\/([^/:]+)/);
  return match?.[1];
}

function getApiBaseUrl(): string {
  const configured = process.env.EXPO_PUBLIC_API_BASE_URL?.trim();
  if (configured) return configured.replace(/\/$/, '');

  const expoHost = getExpoHost();
  if (expoHost) return `http://${expoHost}:8000`;

  if (Platform.OS === 'android') return 'http://10.0.2.2:8000';
  return 'http://localhost:8000';
}

function toScanResult(data: Omit<ScanResult, 'scannedAt'> & { scannedAt: string | Date }): ScanResult {
  return {
    ...data,
    scannedAt: new Date(data.scannedAt),
  };
}

export async function analyzeUrl(url: string): Promise<ScanResult> {
  if (process.env.EXPO_PUBLIC_USE_MOCK_API === 'true') {
    return mockAnalyzeUrl(url);
  }

  const response = await fetch(`${getApiBaseUrl()}/api/v1/analyze`, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ url }),
  });

  if (!response.ok) {
    throw new Error(`Analyze request failed: ${response.status}`);
  }

  return toScanResult(await response.json());
}
