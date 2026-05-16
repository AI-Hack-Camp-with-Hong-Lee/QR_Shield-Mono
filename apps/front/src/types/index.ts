export type RiskLevel = 'safe' | 'caution' | 'danger';

export interface ScanResult {
  id: string;
  url: string;
  riskLevel: RiskLevel;
  score: number;
  explanation: string;
  actionGuide: string;
  signals: string[];
  scannedAt: Date;
}

export type RootStackParamList = {
  Tabs: undefined;
  // result: 히스토리에서 진입 / url: 스캔 후 즉시 진입(스켈레톤 로딩)
  Result: { result: ScanResult } | { url: string };
};

export type TabParamList = {
  Scan: undefined;
  History: undefined;
};
