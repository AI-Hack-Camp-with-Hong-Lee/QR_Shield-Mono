import { Ionicons } from '@expo/vector-icons';
import { CameraView, useCameraPermissions } from 'expo-camera';
import * as Haptics from 'expo-haptics';
import * as ImagePicker from 'expo-image-picker';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  Alert,
  Animated,
  Easing,
  KeyboardAvoidingView,
  Linking,
  Modal,
  Platform,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useIsFocused } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import type { RootStackParamList } from '../types';

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Tabs'>;
};

const SCAN_SIZE = 264;
const CORNER = 30;
const CORNER_THICKNESS = 3;
const ACCENT = '#60A5FA';
const SUCCESS = '#22C55E';
const OVERLAY = 'rgba(2,6,23,0.72)';

export default function ScanScreen({ navigation }: Props) {
  const [permission, requestPermission] = useCameraPermissions();
  const isFocused = useIsFocused();
  const [torch, setTorch] = useState(false);
  const [showUrlInput, setShowUrlInput] = useState(false);
  const [manualUrl, setManualUrl] = useState('');
  const lastScanned = useRef<string | null>(null);

  const scanAnim = useRef(new Animated.Value(0)).current;
  const cornerOpacity = useRef(new Animated.Value(1)).current;
  const successFlash = useRef(new Animated.Value(0)).current;
  const cornerColorAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (isFocused) lastScanned.current = null;
  }, [isFocused]);

  useEffect(() => {
    const sweepLoop = Animated.loop(
      Animated.sequence([
        Animated.timing(scanAnim, { toValue: 1, duration: 2400, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        Animated.timing(scanAnim, { toValue: 0, duration: 2400, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
      ])
    );
    const blink = Animated.loop(
      Animated.sequence([
        Animated.timing(cornerOpacity, { toValue: 0.55, duration: 900, useNativeDriver: true }),
        Animated.timing(cornerOpacity, { toValue: 1, duration: 900, useNativeDriver: true }),
      ])
    );
    sweepLoop.start();
    blink.start();
    return () => { sweepLoop.stop(); blink.stop(); };
  }, []);

  const scanLineY = scanAnim.interpolate({ inputRange: [0, 1], outputRange: [1, SCAN_SIZE - 3] });
  const cornerBorderColor = cornerColorAnim.interpolate({ inputRange: [0, 1], outputRange: [ACCENT, SUCCESS] });

  const triggerSuccessFlash = () => {
    successFlash.setValue(0);
    cornerColorAnim.setValue(0);
    Animated.parallel([
      Animated.sequence([
        Animated.timing(successFlash, { toValue: 0.45, duration: 140, useNativeDriver: true }),
        Animated.timing(successFlash, { toValue: 0, duration: 500, useNativeDriver: true }),
      ]),
      Animated.sequence([
        Animated.timing(cornerColorAnim, { toValue: 1, duration: 140, useNativeDriver: false }),
        Animated.delay(500),
        Animated.timing(cornerColorAnim, { toValue: 0, duration: 300, useNativeDriver: false }),
      ]),
    ]).start();
  };

  // QR 인식 → 즉시 ResultScreen으로 이동 (API 호출은 ResultScreen에서)
  const handleBarCodeScanned = useCallback(
    async ({ data }: { data: string }) => {
      if (data === lastScanned.current) return;
      lastScanned.current = data;

      triggerSuccessFlash();
      await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      navigation.getParent()?.navigate('Result', { url: data } as any);

      setTimeout(() => { lastScanned.current = null; }, 3000);
    },
    [navigation],
  );

  const handleGallery = async () => {
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) {
      Alert.alert('갤러리 권한 필요', '설정에서 사진 접근을 허용해주세요.', [
        { text: '취소', style: 'cancel' },
        { text: '설정 열기', onPress: () => Linking.openSettings() },
      ]);
      return;
    }
    const picked = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], quality: 1 });
    if (!picked.canceled) setShowUrlInput(true);
  };

  const handleManualAnalyze = () => {
    const url = manualUrl.trim();
    if (!url) return;
    setShowUrlInput(false);
    setManualUrl('');
    navigation.getParent()?.navigate('Result', { url } as any);
  };

  // ─── 권한 미허용 ──────────────────────────────────────────────────────────────

  if (!permission) return <View style={styles.container} />;

  if (!permission.granted) {
    return (
      <SafeAreaView style={styles.permissionContainer}>
        <View style={styles.permissionIconWrap}>
          <Ionicons name="shield-checkmark" size={42} color={ACCENT} />
        </View>
        <Text style={styles.permissionTitle}>카메라 권한 필요</Text>
        <Text style={styles.permissionDesc}>
          {permission.canAskAgain
            ? 'QR 코드를 스캔하려면\n카메라 접근을 허용해주세요.'
            : '카메라 권한이 거부되었습니다.\n설정에서 직접 허용해주세요.'}
        </Text>
        <TouchableOpacity
          style={styles.permissionBtn}
          onPress={permission.canAskAgain ? requestPermission : () => Linking.openSettings()}
        >
          <Text style={styles.permissionBtnText}>
            {permission.canAskAgain ? '권한 허용하기' : '설정 열기'}
          </Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  // ─── 스캔 화면 ────────────────────────────────────────────────────────────────

  return (
    <View style={styles.container}>
      {isFocused && (
        <CameraView
          style={StyleSheet.absoluteFillObject}
          facing="back"
          enableTorch={torch}
          onBarcodeScanned={handleBarCodeScanned}
          barcodeScannerSettings={{ barcodeTypes: ['qr'] }}
        />
      )}

      <View style={styles.overlay}>
        <View style={styles.darkenFull} />

        <View style={styles.middleRow}>
          <View style={styles.darkenSide} />
          <View style={styles.scanWindow}>
            <View style={styles.scanClip}>
              <Animated.View style={[styles.successFlashOverlay, { opacity: successFlash }]} pointerEvents="none" />
              <Animated.View style={[styles.scanLine, { transform: [{ translateY: scanLineY }] }]} />
            </View>
            <Animated.View style={[styles.corner, styles.tl, { borderColor: cornerBorderColor, opacity: cornerOpacity }]} />
            <Animated.View style={[styles.corner, styles.tr, { borderColor: cornerBorderColor, opacity: cornerOpacity }]} />
            <Animated.View style={[styles.corner, styles.bl, { borderColor: cornerBorderColor, opacity: cornerOpacity }]} />
            <Animated.View style={[styles.corner, styles.br, { borderColor: cornerBorderColor, opacity: cornerOpacity }]} />
          </View>
          <View style={styles.darkenSide} />
        </View>

        <View style={styles.bottomArea}>
          <Text style={styles.tipText}>QR 코드를 자동으로 인식합니다</Text>
          <View style={styles.controls}>
            <TouchableOpacity style={styles.controlBtn} onPress={handleGallery} activeOpacity={0.75}>
              <Ionicons name="images-outline" size={22} color="#FFFFFF" />
              <Text style={styles.controlLabel}>갤러리</Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.controlBtn, torch && styles.controlBtnOn]}
              onPress={() => setTorch((t) => !t)}
              activeOpacity={0.75}
            >
              <Ionicons name={torch ? 'flashlight' : 'flashlight-outline'} size={22} color={torch ? '#0F172A' : '#FFFFFF'} />
              <Text style={[styles.controlLabel, torch && styles.controlLabelOn]}>{torch ? '켜짐' : '플래시'}</Text>
            </TouchableOpacity>
          </View>
        </View>
      </View>

      <SafeAreaView edges={['top']} style={styles.header} pointerEvents="none">
        <View style={styles.headerRow}>
          <Ionicons name="shield-checkmark" size={20} color={ACCENT} />
          <Text style={styles.headerTitle}>QR Shield</Text>
        </View>
        <Text style={styles.headerSub}>링크를 스캔하고 안전하게 접속하세요</Text>
      </SafeAreaView>

      {/* URL 직접 입력 모달 */}
      <Modal
        visible={showUrlInput}
        transparent
        animationType="slide"
        onRequestClose={() => { setShowUrlInput(false); setManualUrl(''); }}
      >
        <KeyboardAvoidingView style={styles.modalBg} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
          <View style={styles.modalCard}>
            <View style={styles.modalDragHandle} />
            <Ionicons name="link-outline" size={28} color={ACCENT} style={{ alignSelf: 'center' }} />
            <Text style={styles.modalTitle}>URL 직접 입력</Text>
            <Text style={styles.modalDesc}>QR 코드의 링크를 직접 입력하거나 붙여넣으세요.</Text>
            <TextInput
              style={styles.urlInput}
              value={manualUrl}
              onChangeText={setManualUrl}
              placeholder="https://example.com"
              placeholderTextColor="#94A3B8"
              autoCapitalize="none"
              autoCorrect={false}
              keyboardType="url"
              returnKeyType="done"
              onSubmitEditing={handleManualAnalyze}
              autoFocus
            />
            <View style={styles.modalBtns}>
              <TouchableOpacity style={styles.modalCancelBtn} onPress={() => { setShowUrlInput(false); setManualUrl(''); }}>
                <Text style={styles.modalCancelText}>취소</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.modalAnalyzeBtn, !manualUrl.trim() && styles.modalAnalyzeBtnDisabled]}
                onPress={handleManualAnalyze}
                disabled={!manualUrl.trim()}
              >
                <Ionicons name="shield-checkmark-outline" size={16} color="#FFF" />
                <Text style={styles.modalAnalyzeText}>분석하기</Text>
              </TouchableOpacity>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>
    </View>
  );
}

// ─── Styles ───────────────────────────────────────────────────────────────────

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#000' },

  permissionContainer: { flex: 1, backgroundColor: '#0F172A', alignItems: 'center', justifyContent: 'center', padding: 36, gap: 14 },
  permissionIconWrap: { width: 92, height: 92, borderRadius: 26, backgroundColor: 'rgba(96,165,250,0.12)', borderWidth: 1, borderColor: 'rgba(96,165,250,0.25)', alignItems: 'center', justifyContent: 'center', marginBottom: 6 },
  permissionTitle: { fontSize: 22, fontWeight: '800', color: '#F8FAFC', textAlign: 'center' },
  permissionDesc: { fontSize: 14, color: '#94A3B8', textAlign: 'center', lineHeight: 22 },
  permissionBtn: { backgroundColor: ACCENT, paddingHorizontal: 40, paddingVertical: 15, borderRadius: 14, marginTop: 8 },
  permissionBtnText: { color: '#0F172A', fontWeight: '800', fontSize: 15 },

  header: { position: 'absolute', top: 0, left: 0, right: 0, alignItems: 'center', paddingTop: 6, paddingBottom: 14 },
  headerRow: { flexDirection: 'row', alignItems: 'center', gap: 7 },
  headerTitle: { fontSize: 19, fontWeight: '800', color: '#FFFFFF', letterSpacing: 0.2 },
  headerSub: { fontSize: 12, color: 'rgba(255,255,255,0.45)', marginTop: 3 },

  overlay: { flex: 1 },
  darkenFull: { flex: 1, backgroundColor: OVERLAY },
  middleRow: { flexDirection: 'row', height: SCAN_SIZE },
  darkenSide: { flex: 1, backgroundColor: OVERLAY },
  scanWindow: { width: SCAN_SIZE, height: SCAN_SIZE },
  scanClip: { ...StyleSheet.absoluteFillObject, overflow: 'hidden' },

  successFlashOverlay: { ...StyleSheet.absoluteFillObject, backgroundColor: SUCCESS },
  scanLine: { position: 'absolute', left: 6, right: 6, height: 2, backgroundColor: ACCENT, borderRadius: 1, shadowColor: ACCENT, shadowOpacity: 0.9, shadowRadius: 10, shadowOffset: { width: 0, height: 0 } },

  corner: { position: 'absolute', width: CORNER, height: CORNER },
  tl: { top: 0, left: 0, borderTopWidth: CORNER_THICKNESS, borderLeftWidth: CORNER_THICKNESS, borderTopLeftRadius: 5 },
  tr: { top: 0, right: 0, borderTopWidth: CORNER_THICKNESS, borderRightWidth: CORNER_THICKNESS, borderTopRightRadius: 5 },
  bl: { bottom: 0, left: 0, borderBottomWidth: CORNER_THICKNESS, borderLeftWidth: CORNER_THICKNESS, borderBottomLeftRadius: 5 },
  br: { bottom: 0, right: 0, borderBottomWidth: CORNER_THICKNESS, borderRightWidth: CORNER_THICKNESS, borderBottomRightRadius: 5 },

  bottomArea: { flex: 1, backgroundColor: OVERLAY, alignItems: 'center', paddingTop: 36, gap: 28 },
  tipText: { color: 'rgba(255,255,255,0.55)', fontSize: 13, fontWeight: '500' },
  controls: { flexDirection: 'row', gap: 16 },
  controlBtn: { alignItems: 'center', gap: 7, paddingHorizontal: 26, paddingVertical: 14, borderRadius: 50, borderWidth: 1, borderColor: 'rgba(255,255,255,0.18)' },
  controlBtnOn: { backgroundColor: ACCENT, borderColor: ACCENT },
  controlLabel: { color: '#FFFFFF', fontSize: 12, fontWeight: '600' },
  controlLabelOn: { color: '#0F172A' },

  modalBg: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(2,6,23,0.6)' },
  modalCard: { backgroundColor: '#FFFFFF', borderTopLeftRadius: 28, borderTopRightRadius: 28, padding: 28, paddingBottom: 40, gap: 12 },
  modalDragHandle: { width: 38, height: 4, borderRadius: 2, backgroundColor: '#E2E8F0', alignSelf: 'center', marginBottom: 4 },
  modalTitle: { fontSize: 20, fontWeight: '800', color: '#1E293B', textAlign: 'center' },
  modalDesc: { fontSize: 14, color: '#64748B', textAlign: 'center', lineHeight: 21 },
  urlInput: { borderWidth: 1.5, borderColor: '#E2E8F0', borderRadius: 14, paddingHorizontal: 16, paddingVertical: 14, fontSize: 15, color: '#1E293B', marginTop: 4, backgroundColor: '#F8FAFC' },
  modalBtns: { flexDirection: 'row', gap: 10, marginTop: 4 },
  modalCancelBtn: { flex: 1, paddingVertical: 15, borderRadius: 14, backgroundColor: '#F1F5F9', alignItems: 'center' },
  modalCancelText: { fontSize: 15, fontWeight: '700', color: '#64748B' },
  modalAnalyzeBtn: { flex: 2, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingVertical: 15, borderRadius: 14, backgroundColor: ACCENT },
  modalAnalyzeBtnDisabled: { opacity: 0.45 },
  modalAnalyzeText: { fontSize: 15, fontWeight: '700', color: '#FFFFFF' },
});
