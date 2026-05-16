import { Ionicons } from '@expo/vector-icons';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import type { BottomTabBarProps } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import HistoryScreen from '../screens/HistoryScreen';
import ResultScreen from '../screens/ResultScreen';
import ScanScreen from '../screens/ScanScreen';
import type { RootStackParamList, TabParamList } from '../types';
import { useTheme } from '../utils/theme';

const Tab = createBottomTabNavigator<TabParamList>();
const Stack = createNativeStackNavigator<RootStackParamList>();

// ─── 플로팅 탭바 ──────────────────────────────────────────────────────────────

const TAB_META: Record<string, { label: string; icon: string; iconActive: string }> = {
  Scan: { label: '스캔', icon: 'qr-code-outline', iconActive: 'qr-code' },
  History: { label: '기록', icon: 'time-outline', iconActive: 'time' },
};

function FloatingTabBar({ state, navigation }: BottomTabBarProps) {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();

  return (
    <View style={[ftb.outer, { bottom: Math.max(20, insets.bottom + 8) }]}>
      <View
        style={[
          ftb.bar,
          {
            backgroundColor: colors.tabBar,
            borderColor: colors.tabBarBorder,
            shadowColor: colors.shadow,
          },
        ]}
      >
        {state.routes.map((route, index) => {
          const focused = state.index === index;
          const meta = TAB_META[route.name] ?? { label: route.name, icon: 'ellipse-outline', iconActive: 'ellipse' };
          const color = focused ? '#3B82F6' : colors.textMuted;

          const onPress = () => {
            const event = navigation.emit({
              type: 'tabPress',
              target: route.key,
              canPreventDefault: true,
            });
            if (!focused && !event.defaultPrevented) {
              navigation.navigate(route.name);
            }
          };

          return (
            <TouchableOpacity
              key={route.key}
              style={ftb.tab}
              onPress={onPress}
              activeOpacity={0.75}
            >
              <View style={[ftb.pill, focused && ftb.pillActive]}>
                <Ionicons
                  name={(focused ? meta.iconActive : meta.icon) as any}
                  size={20}
                  color={color}
                />
                {focused && (
                  <Text style={[ftb.label, { color }]}>{meta.label}</Text>
                )}
              </View>
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
}

const ftb = StyleSheet.create({
  outer: {
    position: 'absolute',
    left: 32,
    right: 32,
    alignItems: 'center',
  },
  bar: {
    flexDirection: 'row',
    borderRadius: 26,
    borderWidth: 1,
    paddingVertical: 6,
    paddingHorizontal: 6,
    shadowOpacity: 0.14,
    shadowRadius: 24,
    shadowOffset: { width: 0, height: 6 },
    elevation: 12,
    gap: 4,
  },
  tab: {
    flex: 1,
    alignItems: 'center',
  },
  pill: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingHorizontal: 18,
    paddingVertical: 10,
    borderRadius: 20,
    minWidth: 48,
  },
  pillActive: {
    backgroundColor: 'rgba(59,130,246,0.12)',
  },
  label: {
    fontSize: 13,
    fontWeight: '700',
    letterSpacing: 0.1,
  },
});

// ─── 탭 네비게이터 ────────────────────────────────────────────────────────────

function TabNavigator() {
  return (
    <Tab.Navigator
      tabBar={(props) => <FloatingTabBar {...props} />}
      screenOptions={{ headerShown: false }}
    >
      <Tab.Screen name="Scan" component={ScanScreen} />
      <Tab.Screen name="History" component={HistoryScreen} />
    </Tab.Navigator>
  );
}

// ─── 루트 네비게이터 ──────────────────────────────────────────────────────────

export default function RootNavigator() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Tabs" component={TabNavigator} />
      <Stack.Screen
        name="Result"
        component={ResultScreen}
        options={{ presentation: 'modal', animation: 'slide_from_bottom' }}
      />
    </Stack.Navigator>
  );
}
