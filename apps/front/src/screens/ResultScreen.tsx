import { Ionicons } from '@expo/vector-icons';
import * as Clipboard from 'expo-clipboard';
import * as Haptics from 'expo-haptics';
import { useEffect, useRef, useState } from 'react';
import {
  Animated,
  Easing,
  Linking,
  ScrollView,
  Share,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Svg, { Circle } from 'react-native-svg';
import type { BottomTabNavigationProp } from '@react-navigation/bottom-tabs';
import type { RouteProp } from '@react-navigation/native';
import { analyzeUrl } from '../services/api';
import { useStore } from '../store/useStore';
import type { ScanResult, TabParamList } from '../types';
import { RISK_CONFIG } from '../utils/riskConfig';
import { useTheme } from '../utils/theme';

type Props = {
  navigation: BottomTabNavigationProp<TabParamList, 'Result'>;
  route: RouteProp<TabParamList, 'Result'>;
};

// ─── Toast ───────────────────────────────────────────────────────────────────

function useToast() {
  const [message, setMessage] = useState('');
  const opacity = useRef(new Animated.Value(0)).current;
  const translateY = useRef(new Animated.Value(12)).current;

  const show = (msg: string) => {
    setMessage(msg);
    opacity.setValue(0);
    translateY.setValue(12);
    Animated.sequence([
      Animated.parallel([
        Animated.timing(opacity, { toValue: 1, duration: 180, useNativeDriver: true }),
        Animated.timing(translateY, { toValue: 0, duration: 180, easing: Easing.out(Easing.quad), useNativeDriver: true }),
      ]),
      Animated.delay(1600),
      Animated.timing(opacity, { toValue: 0, duration: 220, useNativeDriver: true }),
    ]).start();
  };

  return { message, opacity, translateY, show };
}

// ─── 원형 스코어 게이지 ───────────────────────────────────────────────────────

const GAUGE_R = 72;
const GAUGE_SW = 15;
const GAUGE_SIZE = (GAUGE_R + GAUGE_SW + 4) * 2;
const GAUGE_CX = GAUGE_SIZE / 2;
const GAUGE_CY = GAUGE_SIZE / 2;
const CIRCUMFERENCE = 2 * Math.PI * GAUGE_R;
const TRACK_LENGTH = CIRCUMFERENCE * 0.75; // 270° arc
const ROTATION = 135; // gap at bottom

function ScoreGauge({
  score,
  color,
  displayScore,
  isDark,
}: {
  score: number;
  color: string;
  displayScore: number;
  isDark: boolean;
}) {
  const [progressLength, setProgressLength] = useState(0);
  const progressAnim = useRef(new Animated.Value(0)).current;
  const trackColor = isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.07)';

  useEffect(() => {
    progressAnim.addListener(({ value }: { value: number }) => setProgressLength(value));
    Animated.timing(progressAnim, {
      toValue: (TRACK_LENGTH * score) / 100,
      duration: 1200,
      delay: 300,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: false,
    }).start();
    return () => progressAnim.removeAllListeners();
  }, [score]);

  return (
    <View style={{ alignItems: 'center' }}>
      <View style={{ width: GAUGE_SIZE, height: GAUGE_SIZE }}>
        <Svg width={GAUGE_SIZE} height={GAUGE_SIZE}>
          {/* 트랙 */}
          <Circle
            cx={GAUGE_CX}
            cy={GAUGE_CY}
            r={GAUGE_R}
            fill="none"
            stroke={trackColor}
            strokeWidth={GAUGE_SW}
            strokeDasharray={[TRACK_LENGTH, CIRCUMFERENCE - TRACK_LENGTH]}
            strokeLinecap="round"
            transform={`rotate(${ROTATION}, ${GAUGE_CX}, ${GAUGE_CY})`}
          />
          {/* 진행 */}
          {progressLength > 2 && (
            <Circle
              cx={GAUGE_CX}
              cy={GAUGE_CY}
              r={GAUGE_R}
              fill="none"
              stroke={color}
              strokeWidth={GAUGE_SW}
              strokeDasharray={[progressLength, CIRCUMFERENCE - progressLength]}
              strokeLinecap="round"
              transform={`rotate(${ROTATION}, ${GAUGE_CX}, ${GAUGE_CY})`}
            />
          )}
        </Svg>

        {/* 중앙 점수 텍스트 */}
        <View style={[StyleSheet.absoluteFillObject, gauge.center]}>
          <Text style={[gauge.scoreNum, { color }]}>{displayScore}</Text>
          <Text style={gauge.scoreSub}>/ 100점</Text>
        </View>
      </View>
    </View>
  );
}

const gauge = StyleSheet.create({
  center: { alignItems: 'center', justifyContent: 'center', paddingBottom: 18 },
  scoreNum: { fontSize: 40, fontWeight: '800', lineHeight: 44 },
  scoreSub: { fontSize: 13, color: '#94A3B8', fontWeight: '500', marginTop: 2 },
});

// ─── 스켈레톤 로딩 ────────────────────────────────────────────────────────────

function SkeletonResult() {
  const { colors, isDark } = useTheme();
  const pulse = useRef(new Animated.Value(0.5)).current;
  const skeletonBg = isDark ? '#243147' : '#E2E8F0';

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 1, duration: 800, useNativeDriver: true }),
        Animated.timing(pulse, { toValue: 0.5, duration: 800, useNativeDriver: true }),
      ])
    ).start();
    return () => pulse.stopAnimation();
  }, []);

  const Bone = ({ w, h, r = 10, mt = 0 }: { w: number | string; h: number; r?: number; mt?: number }) => (
    <Animated.View
      style={{ width: w as any, height: h, borderRadius: r, backgroundColor: skeletonBg, opacity: pulse, marginTop: mt }}
    />
  );

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.bg }]} edges={['bottom']}>
      <View style={styles.dragHandleArea}>
        <Bone w={38} h={4} r={2} />
      </View>
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <Bone w={40} h={40} r={20} />
        <Bone w={80} h={16} r={8} />
        <Bone w={40} h={40} r={20} />
      </View>
      <ScrollView contentContainerStyle={skel.scroll} showsVerticalScrollIndicator={false}>
        {/* 히어로 카드 스켈레톤 */}
        <Bone w="100%" h={300} r={22} />
        {/* 카드 스켈레톤 */}
        <Bone w="100%" h={88} r={16} mt={14} />
        <Bone w="100%" h={110} r={16} mt={14} />
        <Bone w="60%" h={14} r={7} mt={14} />
        <Bone w="100%" h={54} r={16} mt={14} />
        <Bone w="100%" h={54} r={16} mt={10} />
      </ScrollView>
    </SafeAreaView>
  );
}

const skel = StyleSheet.create({
  scroll: { paddingHorizontal: 20, paddingTop: 8, paddingBottom: 32 },
});

// ─── 결과 화면 ────────────────────────────────────────────────────────────────

function ResultContent({
  result,
  navigation,
}: {
  result: ScanResult;
  navigation: Props['navigation'];
}) {
  const config = RISK_CONFIG[result.riskLevel];
  const { colors, isDark } = useTheme();
  const toast = useToast();

  const [displayScore, setDisplayScore] = useState(0);
  const scoreValue = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(48)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(slideAnim, { toValue: 0, duration: 380, easing: Easing.out(Easing.cubic), useNativeDriver: true }),
      Animated.timing(fadeAnim, { toValue: 1, duration: 320, useNativeDriver: true }),
    ]).start();

    scoreValue.addListener(({ value }: { value: number }) => setDisplayScore(Math.round(value)));
    Animated.timing(scoreValue, {
      toValue: result.score,
      duration: 1000,
      delay: 200,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: false,
    }).start();

    return () => scoreValue.removeAllListeners();
  }, []);

  const riskMeta = {
    safe: { label: '안전한 링크입니다', subtitle: '이 URL은 안전한 것으로 분석되었습니다.' },
    caution: { label: '주의가 필요합니다', subtitle: '접속 전 URL을 한 번 더 확인하세요.' },
    danger: { label: '위험한 링크입니다', subtitle: '이 URL에 접속하지 마세요.' },
  }[result.riskLevel];

  const handleCopy = async () => {
    await Clipboard.setStringAsync(result.url);
    await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    toast.show('URL이 복사되었습니다');
  };

  return (
    <Animated.ScrollView
      contentContainerStyle={styles.scroll}
      showsVerticalScrollIndicator={false}
      style={{ opacity: fadeAnim, transform: [{ translateY: slideAnim }] }}
    >
      {/* 히어로 카드 */}
      <View style={[styles.heroCard, { backgroundColor: config.bg, borderColor: config.borderColor }]}>
        {/* 아이콘 + 텍스트 */}
        <View style={styles.heroTop}>
          <View style={[styles.iconCircle, { backgroundColor: config.borderColor }]}>
            <Ionicons name={config.icon as any} size={28} color={config.color} />
          </View>
          <View style={styles.heroText}>
            <Text style={[styles.heroLabel, { color: config.color }]}>{riskMeta.label}</Text>
            <Text style={[styles.heroSub, { color: colors.textSub }]}>{riskMeta.subtitle}</Text>
          </View>
        </View>

        {/* 원형 게이지 */}
        <ScoreGauge score={result.score} color={config.color} displayScore={displayScore} isDark={isDark} />

        {/* 위험도 레이블 */}
        <View style={[styles.riskPill, { backgroundColor: config.borderColor, alignSelf: 'center' }]}>
          <View style={[styles.riskDot, { backgroundColor: config.color }]} />
          <Text style={[styles.riskPillText, { color: config.color }]}>{config.label}</Text>
        </View>
      </View>

      {/* URL 카드 */}
      <View style={[styles.card, { backgroundColor: colors.card, shadowColor: colors.shadow }]}>
        <View style={styles.cardHeader}>
          <Text style={styles.cardLabel}>스캔된 URL</Text>
          <TouchableOpacity onPress={handleCopy} style={[styles.copyBtn, { backgroundColor: colors.surface }]} activeOpacity={0.7}>
            <Ionicons name="copy-outline" size={15} color={colors.textSub} />
            <Text style={[styles.copyBtnText, { color: colors.textSub }]}>복사</Text>
          </TouchableOpacity>
        </View>
        <Text style={styles.urlText} numberOfLines={3}>{result.url}</Text>
      </View>

      {/* AI 분석 */}
      <View style={[styles.card, { backgroundColor: colors.card, shadowColor: colors.shadow }]}>
        <Text style={styles.cardLabel}>AI 분석</Text>
        <Text style={[styles.bodyText, { color: colors.textSub }]}>{result.explanation}</Text>
      </View>

      {/* 위험 신호 */}
      {result.signals.length > 0 && (
        <View style={[styles.card, { backgroundColor: colors.card, shadowColor: colors.shadow }]}>
          <Text style={styles.cardLabel}>탐지된 위험 신호</Text>
          <View style={styles.signalList}>
            {result.signals.map((signal: string, i: number) => (
              <View key={i} style={styles.signalRow}>
                <View style={[styles.signalBullet, { backgroundColor: config.color }]} />
                <Text style={[styles.signalText, { color: colors.textSub }]}>{signal}</Text>
              </View>
            ))}
          </View>
        </View>
      )}

      {/* 행동 가이드 */}
      <View style={[styles.guideBox, { backgroundColor: config.bg, borderColor: config.borderColor }]}>
        <Ionicons name="information-circle-outline" size={20} color={config.color} />
        <Text style={[styles.guideText, { color: config.color }]}>{result.actionGuide}</Text>
      </View>

      {/* 버튼 */}
      <View style={styles.btnGroup}>
        {result.riskLevel !== 'danger' && (
          <TouchableOpacity style={[styles.btn, { backgroundColor: config.color }]} onPress={() => Linking.openURL(result.url)} activeOpacity={0.8}>
            <Ionicons name="open-outline" size={18} color="#FFF" />
            <Text style={styles.btnTextWhite}>URL 열기</Text>
          </TouchableOpacity>
        )}
        <TouchableOpacity style={[styles.btnOutline, { backgroundColor: colors.surface }]} onPress={() => navigation.goBack()} activeOpacity={0.75}>
          <Ionicons name="qr-code-outline" size={18} color={colors.text} />
          <Text style={[styles.btnTextDark, { color: colors.text }]}>다시 스캔</Text>
        </TouchableOpacity>
      </View>
    </Animated.ScrollView>
  );
}

// ─── 메인 컴포넌트 ────────────────────────────────────────────────────────────

export default function ResultScreen({ navigation, route }: Props) {
  const params = route.params;
  const { colors } = useTheme();
  const addScan = useStore((s) => s.addScan);
  const toast = useToast();

  const hasResult = 'result' in params;
  const [result, setResult] = useState<ScanResult | undefined>(
    hasResult ? (params as { result: ScanResult }).result : undefined
  );
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    if (!hasResult) {
      const url = (params as { url: string }).url;
      analyzeUrl(url)
        .then((r) => {
          setResult(r);
          addScan(r);
          if (r.riskLevel === 'danger') {
            Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
          } else if (r.riskLevel === 'caution') {
            Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
          }
        })
        .catch(() => setLoadError(true));
    }
  }, []);

  if (loadError) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: colors.bg }]} edges={['bottom']}>
        <View style={styles.dragHandleArea}>
          <View style={[styles.dragHandle, { backgroundColor: colors.border }]} />
        </View>
        <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', gap: 14, padding: 32 }}>
          <Ionicons name="alert-circle-outline" size={56} color="#EF4444" />
          <Text style={{ fontSize: 18, fontWeight: '700', color: colors.text, textAlign: 'center' }}>분석에 실패했습니다</Text>
          <Text style={{ fontSize: 14, color: colors.textSub, textAlign: 'center', lineHeight: 21 }}>서버와 연결할 수 없습니다. 잠시 후 다시 시도해주세요.</Text>
          <TouchableOpacity style={[styles.btn, { backgroundColor: '#3B82F6', marginTop: 8 }]} onPress={() => navigation.goBack()}>
            <Ionicons name="arrow-back" size={18} color="#FFF" />
            <Text style={styles.btnTextWhite}>돌아가기</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  if (!result) {
    return <SkeletonResult />;
  }

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.bg }]} edges={['bottom']}>
      {/* 드래그 핸들 */}
      <View style={styles.dragHandleArea}>
        <View style={[styles.dragHandle, { backgroundColor: colors.border }]} />
      </View>

      {/* 헤더 */}
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={[styles.iconBtn, { backgroundColor: colors.surface }]}>
          <Ionicons name="chevron-down" size={22} color={colors.textSub} />
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: colors.text }]}>분석 결과</Text>
        <TouchableOpacity onPress={async () => {
          await Share.share({
            message: `[QR Shield]\n위험도: ${RISK_CONFIG[result.riskLevel].label} (${result.score}/100)\nURL: ${result.url}`,
            url: result.url,
          });
        }} style={[styles.iconBtn, { backgroundColor: colors.surface }]}>
          <Ionicons name="share-outline" size={20} color={colors.textSub} />
        </TouchableOpacity>
      </View>

      <ResultContent result={result} navigation={navigation} />

      {/* 토스트 */}
      <Animated.View
        style={[styles.toast, { opacity: toast.opacity, transform: [{ translateY: toast.translateY }] }]}
        pointerEvents="none"
      >
        <Ionicons name="checkmark-circle" size={16} color="#FFFFFF" />
        <Text style={styles.toastText}>{toast.message}</Text>
      </Animated.View>
    </SafeAreaView>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { paddingHorizontal: 20, paddingBottom: 28, gap: 14 },

  dragHandleArea: { alignItems: 'center', paddingTop: 12, paddingBottom: 4 },
  dragHandle: { width: 38, height: 4, borderRadius: 2 },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  iconBtn: { width: 40, height: 40, borderRadius: 20, alignItems: 'center', justifyContent: 'center' },
  headerTitle: { fontSize: 16, fontWeight: '700' },

  // 히어로 카드
  heroCard: { borderRadius: 22, borderWidth: 1.5, padding: 22, gap: 14, marginTop: 8 },
  heroTop: { flexDirection: 'row', alignItems: 'flex-start', gap: 14 },
  iconCircle: { width: 52, height: 52, borderRadius: 16, alignItems: 'center', justifyContent: 'center' },
  heroText: { flex: 1, gap: 4, paddingTop: 2 },
  heroLabel: { fontSize: 18, fontWeight: '800', letterSpacing: 0.1 },
  heroSub: { fontSize: 13, lineHeight: 18 },

  riskPill: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 12, paddingVertical: 6, borderRadius: 100 },
  riskDot: { width: 6, height: 6, borderRadius: 3 },
  riskPillText: { fontSize: 13, fontWeight: '700' },

  // 카드
  card: { borderRadius: 16, padding: 18, gap: 10, shadowOpacity: 0.05, shadowRadius: 10, shadowOffset: { width: 0, height: 2 }, elevation: 2 },
  cardHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  cardLabel: { fontSize: 11, fontWeight: '700', color: '#94A3B8', textTransform: 'uppercase', letterSpacing: 0.7 },
  copyBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8 },
  copyBtnText: { fontSize: 12, fontWeight: '600' },
  urlText: { fontSize: 14, color: '#3B82F6', fontWeight: '500', lineHeight: 20 },
  bodyText: { fontSize: 14, lineHeight: 23 },

  signalList: { gap: 10 },
  signalRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 10 },
  signalBullet: { width: 6, height: 6, borderRadius: 3, marginTop: 6 },
  signalText: { flex: 1, fontSize: 14, lineHeight: 21 },

  guideBox: { flexDirection: 'row', alignItems: 'flex-start', gap: 10, padding: 16, borderRadius: 14, borderWidth: 1 },
  guideText: { flex: 1, fontSize: 14, fontWeight: '500', lineHeight: 21 },

  // 버튼
  btnGroup: { gap: 10, marginTop: 4 },
  btn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingVertical: 16, borderRadius: 16 },
  btnTextWhite: { color: '#FFF', fontWeight: '700', fontSize: 15 },
  btnOutline: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingVertical: 16, borderRadius: 16 },
  btnTextDark: { fontWeight: '700', fontSize: 15 },

  // 토스트
  toast: {
    position: 'absolute', bottom: 36, alignSelf: 'center',
    flexDirection: 'row', alignItems: 'center', gap: 8,
    backgroundColor: '#1E293B', paddingHorizontal: 18, paddingVertical: 11, borderRadius: 100,
    shadowColor: '#000', shadowOpacity: 0.18, shadowRadius: 12, shadowOffset: { width: 0, height: 4 }, elevation: 8,
  },
  toastText: { color: '#FFFFFF', fontSize: 13, fontWeight: '600' },
});
