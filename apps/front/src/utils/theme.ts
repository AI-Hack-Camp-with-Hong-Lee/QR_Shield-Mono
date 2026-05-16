import { useColorScheme } from 'react-native';

export const Colors = {
  light: {
    bg: '#F8FAFC',
    card: '#FFFFFF',
    text: '#1E293B',
    textSub: '#64748B',
    textMuted: '#94A3B8',
    border: '#E2E8F0',
    surface: '#F1F5F9',
    tabBar: 'rgba(255,255,255,0.94)',
    tabBarBorder: 'rgba(0,0,0,0.07)',
    shadow: '#0F172A',
  },
  dark: {
    bg: '#0B1120',
    card: '#1A2438',
    text: '#F1F5F9',
    textSub: '#94A3B8',
    textMuted: '#475569',
    border: '#243147',
    surface: '#1E293B',
    tabBar: 'rgba(15,23,42,0.94)',
    tabBarBorder: 'rgba(255,255,255,0.08)',
    shadow: '#000000',
  },
} as const;

export type ThemeColors = typeof Colors.light;

export function useTheme() {
  const scheme = useColorScheme();
  const isDark = scheme === 'dark';
  return { colors: isDark ? Colors.dark : Colors.light, isDark };
}
