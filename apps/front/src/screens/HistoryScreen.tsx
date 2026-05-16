import { Ionicons } from '@expo/vector-icons';
import { useRef, useState } from 'react';
import {
  Alert,
  Animated,
  PanResponder,
  SectionList,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
  useWindowDimensions,
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { RiskBadge } from '../components/RiskBadge';
import { useStore } from '../store/useStore';
import type { RootStackParamList, RiskLevel, ScanResult } from '../types';
import { RISK_CONFIG } from '../utils/riskConfig';
import { useTheme } from '../utils/theme';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Tabs'>;
};

// ─── 탭 설정 ─────────────────────────────────────────────────────────────────

const TABS = ['전체', '안전', '주의', '위험'] as const;
type Tab = (typeof TABS)[number];

const TAB_RISK: Record<Tab, RiskLevel | null> = {
  전체: null,
  안전: 'safe',
  주의: 'caution',
  위험: 'danger',
};

// ─── 헬퍼 ────────────────────────────────────────────────────────────────────

function getDomain(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url.slice(0, 40);
  }
}

function formatTime(date: Date): string {
  const d = new Date(date);
  const now = new Date();
  const diffMin = Math.floor((now.getTime() - d.getTime()) / 60000);
  if (diffMin < 1) return '방금 전';
  if (diffMin < 60) return `${diffMin}분 전`;
  const diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return `${diffHour}시간 전`;
  return d.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
}

function groupByDate(items: ScanResult[]): { title: string; data: ScanResult[] }[] {
  const startOf = (d: Date) => { d.setHours(0, 0, 0, 0); return d; };
  const today = startOf(new Date()).getTime();
  const yesterday = today - 86400000;
  const weekAgo = today - 7 * 86400000;

  const buckets: Record<string, ScanResult[]> = { 오늘: [], 어제: [], '이번 주': [], 이전: [] };

  for (const item of items) {
    const t = startOf(new Date(item.scannedAt)).getTime();
    if (t === today) buckets['오늘'].push(item);
    else if (t === yesterday) buckets['어제'].push(item);
    else if (t >= weekAgo) buckets['이번 주'].push(item);
    else buckets['이전'].push(item);
  }

  return Object.entries(buckets)
    .filter(([, data]) => data.length > 0)
    .map(([title, data]) => ({ title, data }));
}

// ─── 필터 탭 ─────────────────────────────────────────────────────────────────

function FilterTabs({
  active,
  counts,
  onSelect,
}: {
  active: Tab;
  counts: Record<Tab, number>;
  onSelect: (tab: Tab) => void;
}) {
  const { colors } = useTheme();
  const { width } = useWindowDimensions();
  const tabWidth = (width - 40) / TABS.length;
  const indicatorX = useRef(new Animated.Value(0)).current;

  const handlePress = (tab: Tab, idx: number) => {
    Animated.spring(indicatorX, {
      toValue: idx * tabWidth,
      useNativeDriver: true,
      tension: 120,
      friction: 12,
    }).start();
    onSelect(tab);
  };

  return (
    <View style={[tabs.container, { backgroundColor: colors.surface }]}>
      <Animated.View
        style={[
          tabs.indicator,
          {
            width: tabWidth,
            backgroundColor: colors.card,
            shadowColor: colors.shadow,
            transform: [{ translateX: indicatorX }],
          },
        ]}
      />
      {TABS.map((tab, idx) => {
        const isActive = active === tab;
        return (
          <TouchableOpacity
            key={tab}
            style={[tabs.tab, { width: tabWidth }]}
            onPress={() => handlePress(tab, idx)}
            activeOpacity={0.7}
          >
            <Text style={[tabs.label, { color: isActive ? colors.text : colors.textMuted }]}>
              {tab}
            </Text>
            {counts[tab] > 0 && (
              <View style={[tabs.badge, isActive && tabs.badgeActive]}>
                <Text style={[tabs.badgeText, isActive && tabs.badgeTextActive]}>
                  {counts[tab]}
                </Text>
              </View>
            )}
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

// ─── 아이템 콘텐츠 ────────────────────────────────────────────────────────────

function ItemContent({ item }: { item: ScanResult }) {
  const { colors } = useTheme();
  const config = RISK_CONFIG[item.riskLevel];
  return (
    <View style={[styles.item, { backgroundColor: colors.card, shadowColor: colors.shadow }]}>
      <View style={[styles.itemIcon, { backgroundColor: config.bg }]}>
        <Ionicons name={config.icon as any} size={20} color={config.color} />
      </View>
      <View style={styles.itemBody}>
        <Text style={[styles.itemDomain, { color: colors.text }]} numberOfLines={1}>
          {getDomain(item.url)}
        </Text>
        <Text style={[styles.itemUrl, { color: colors.textMuted }]} numberOfLines={1}>
          {item.url}
        </Text>
        <Text style={[styles.itemTime, { color: colors.textMuted }]}>
          {formatTime(item.scannedAt)}
        </Text>
      </View>
      <RiskBadge level={item.riskLevel} size="sm" />
    </View>
  );
}

// ─── 스와이프 아이템 ──────────────────────────────────────────────────────────

const DELETE_WIDTH = 80;

function SwipeableItem({
  item,
  onPress,
  onDelete,
}: {
  item: ScanResult;
  onPress: () => void;
  onDelete: () => void;
}) {
  const { width } = useWindowDimensions();
  const itemWidth = width - 40;
  const translateX = useRef(new Animated.Value(0)).current;
  const isOpen = useRef(false);

  const snapTo = (toValue: number) => {
    Animated.spring(translateX, {
      toValue,
      useNativeDriver: true,
      tension: 100,
      friction: 12,
    }).start();
  };

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => false,
      onMoveShouldSetPanResponder: (_, { dx, dy }) =>
        Math.abs(dx) > 6 && Math.abs(dx) > Math.abs(dy) * 1.8,

      onPanResponderGrant: () => {
        translateX.setOffset(isOpen.current ? -DELETE_WIDTH : 0);
        translateX.setValue(0);
      },

      onPanResponderMove: (_, { dx }) => {
        translateX.setValue(Math.min(0, Math.max(-DELETE_WIDTH, dx)));
      },

      onPanResponderRelease: (_, { dx }) => {
        translateX.flattenOffset();
        if (!isOpen.current && dx < -DELETE_WIDTH / 2) {
          snapTo(-DELETE_WIDTH);
          isOpen.current = true;
        } else if (isOpen.current && dx > DELETE_WIDTH / 2) {
          snapTo(0);
          isOpen.current = false;
        } else {
          snapTo(isOpen.current ? -DELETE_WIDTH : 0);
        }
      },

      onPanResponderTerminate: () => {
        translateX.flattenOffset();
        snapTo(isOpen.current ? -DELETE_WIDTH : 0);
      },
    })
  ).current;

  const handlePress = () => {
    if (isOpen.current) {
      snapTo(0);
      isOpen.current = false;
    } else {
      onPress();
    }
  };

  return (
    <View style={{ width: itemWidth, overflow: 'hidden', borderRadius: 16 }}>
      <Animated.View
        style={{ flexDirection: 'row', width: itemWidth + DELETE_WIDTH, transform: [{ translateX }] }}
        {...panResponder.panHandlers}
      >
        <TouchableOpacity style={{ width: itemWidth }} onPress={handlePress} activeOpacity={0.75}>
          <ItemContent item={item} />
        </TouchableOpacity>
        <TouchableOpacity style={styles.deleteArea} onPress={onDelete} activeOpacity={0.85}>
          <Ionicons name="trash-outline" size={20} color="#FFF" />
          <Text style={styles.deleteText}>삭제</Text>
        </TouchableOpacity>
      </Animated.View>
    </View>
  );
}

// ─── 메인 화면 ────────────────────────────────────────────────────────────────

export default function HistoryScreen({ navigation }: Props) {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  const history = useStore((s) => s.history);
  const clearHistory = useStore((s) => s.clearHistory);
  const deleteScan = useStore((s) => s.deleteScan);
  const [activeTab, setActiveTab] = useState<Tab>('전체');

  const counts: Record<Tab, number> = {
    전체: history.length,
    안전: history.filter((h) => h.riskLevel === 'safe').length,
    주의: history.filter((h) => h.riskLevel === 'caution').length,
    위험: history.filter((h) => h.riskLevel === 'danger').length,
  };

  const filtered =
    TAB_RISK[activeTab] === null
      ? history
      : history.filter((h) => h.riskLevel === TAB_RISK[activeTab]);

  const sections = groupByDate(filtered);

  // 플로팅 탭바 높이 보정
  const bottomPadding = Math.max(20, insets.bottom + 8) + 72;

  const handleClear = () => {
    Alert.alert('전체 삭제', '스캔 기록을 모두 삭제할까요?', [
      { text: '취소', style: 'cancel' },
      { text: '삭제', style: 'destructive', onPress: clearHistory },
    ]);
  };

  const handleDelete = (id: string) => {
    Alert.alert('삭제', '이 기록을 삭제할까요?', [
      { text: '취소', style: 'cancel' },
      { text: '삭제', style: 'destructive', onPress: () => deleteScan(id) },
    ]);
  };

  // ─── 빈 상태 ──────────────────────────────────────────────────────────────

  if (history.length === 0) {
    return (
      <SafeAreaView style={[styles.container, { backgroundColor: colors.bg }]} edges={['top']}>
        <View style={styles.header}>
          <Text style={[styles.pageTitle, { color: colors.text }]}>스캔 기록</Text>
        </View>
        <View style={styles.emptyBody}>
          <View style={[styles.emptyIconWrap, { backgroundColor: colors.surface }]}>
            <Ionicons name="time-outline" size={36} color={colors.textMuted} />
          </View>
          <Text style={[styles.emptyTitle, { color: colors.textMuted }]}>스캔 기록이 없습니다</Text>
          <Text style={[styles.emptyDesc, { color: colors.textMuted }]}>
            QR 코드를 스캔하면{'\n'}여기에 기록이 남습니다.
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  // ─── 목록 ─────────────────────────────────────────────────────────────────

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: colors.bg }]} edges={['top']}>
      <View style={styles.header}>
        <Text style={[styles.pageTitle, { color: colors.text }]}>스캔 기록</Text>
        <TouchableOpacity onPress={handleClear} style={styles.clearBtn}>
          <Ionicons name="trash-outline" size={15} color="#EF4444" />
          <Text style={styles.clearText}>전체 삭제</Text>
        </TouchableOpacity>
      </View>

      <FilterTabs active={activeTab} counts={counts} onSelect={setActiveTab} />

      {filtered.length === 0 ? (
        <View style={styles.emptyBody}>
          <View style={[styles.emptyIconWrap, { backgroundColor: colors.surface }]}>
            <Ionicons name="search-outline" size={30} color={colors.textMuted} />
          </View>
          <Text style={[styles.emptyTitle, { color: colors.textMuted }]}>해당 기록이 없습니다</Text>
        </View>
      ) : (
        <SectionList
          sections={sections}
          keyExtractor={(item) => item.id}
          renderSectionHeader={({ section: { title } }) => (
            <View style={styles.sectionHeader}>
              <Text style={[styles.sectionTitle, { color: colors.textMuted }]}>{title}</Text>
            </View>
          )}
          renderItem={({ item }) => (
            <View style={styles.itemWrapper}>
              <SwipeableItem
                item={item}
                onPress={() => navigation.navigate('Result', { result: item })}
                onDelete={() => handleDelete(item.id)}
              />
            </View>
          )}
          contentContainerStyle={[styles.list, { paddingBottom: bottomPadding }]}
          showsVerticalScrollIndicator={false}
          stickySectionHeadersEnabled={false}
        />
      )}
    </SafeAreaView>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const tabs = StyleSheet.create({
  container: {
    flexDirection: 'row',
    marginHorizontal: 20,
    marginBottom: 12,
    borderRadius: 12,
    padding: 4,
    position: 'relative',
  },
  indicator: {
    position: 'absolute',
    top: 4,
    left: 4,
    bottom: 4,
    borderRadius: 9,
    shadowOpacity: 0.07,
    shadowRadius: 4,
    shadowOffset: { width: 0, height: 1 },
    elevation: 2,
  },
  tab: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 8,
    gap: 4,
    zIndex: 1,
  },
  label: { fontSize: 13, fontWeight: '600' },
  badge: {
    backgroundColor: '#E2E8F0',
    borderRadius: 100,
    paddingHorizontal: 5,
    paddingVertical: 1,
    minWidth: 18,
    alignItems: 'center',
  },
  badgeActive: { backgroundColor: '#EFF6FF' },
  badgeText: { fontSize: 10, fontWeight: '700', color: '#94A3B8' },
  badgeTextActive: { color: '#3B82F6' },
});

const styles = StyleSheet.create({
  container: { flex: 1 },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 8,
    paddingBottom: 14,
  },
  pageTitle: { fontSize: 26, fontWeight: '800' },
  clearBtn: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  clearText: { fontSize: 13, color: '#EF4444', fontWeight: '600' },

  list: { paddingHorizontal: 20 },
  sectionHeader: { paddingBottom: 8, paddingTop: 4 },
  sectionTitle: { fontSize: 12, fontWeight: '700', letterSpacing: 0.4 },
  itemWrapper: { marginBottom: 8 },

  item: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 16,
    padding: 14,
    gap: 12,
    shadowOpacity: 0.05,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  itemIcon: { width: 44, height: 44, borderRadius: 13, alignItems: 'center', justifyContent: 'center' },
  itemBody: { flex: 1, gap: 2 },
  itemDomain: { fontSize: 14, fontWeight: '700' },
  itemUrl: { fontSize: 12, lineHeight: 16 },
  itemTime: { fontSize: 11, marginTop: 1 },

  deleteArea: {
    width: DELETE_WIDTH,
    backgroundColor: '#EF4444',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
  },
  deleteText: { fontSize: 11, fontWeight: '700', color: '#FFFFFF' },

  emptyBody: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12, paddingBottom: 60 },
  emptyIconWrap: { width: 80, height: 80, borderRadius: 24, alignItems: 'center', justifyContent: 'center' },
  emptyTitle: { fontSize: 17, fontWeight: '700' },
  emptyDesc: { fontSize: 14, textAlign: 'center', lineHeight: 21 },
});
