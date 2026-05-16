import type { RiskLevel } from '../types';

export const RISK_CONFIG: Record<
  RiskLevel,
  { label: string; color: string; bg: string; icon: string; borderColor: string }
> = {
  safe: {
    label: '안전',
    color: '#16A34A',
    bg: '#DCFCE7',
    icon: 'shield-checkmark',
    borderColor: '#86EFAC',
  },
  caution: {
    label: '주의',
    color: '#D97706',
    bg: '#FEF3C7',
    icon: 'warning',
    borderColor: '#FCD34D',
  },
  danger: {
    label: '위험',
    color: '#DC2626',
    bg: '#FEE2E2',
    icon: 'shield',
    borderColor: '#FCA5A5',
  },
};
