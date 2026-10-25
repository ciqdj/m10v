#!/bin/bash
set -euo pipefail
if [[ "${1:-}" == "--help" || $# -lt 1 ]]; then
  echo "Usage: $0 OUTPUT_DIRECTORY [SECONDS=180] [--build-only]"
  echo "Builds a macOS read/notify-only camera probe; normal run requests Bluetooth permission."
  exit 0
fi
probe_output="$1"
probe_seconds="${2:-180}"
[[ "$probe_seconds" =~ ^[0-9]+$ ]] && (( probe_seconds >= 10 && probe_seconds <= 600 )) || { echo 'SECONDS must be 10..600' >&2; exit 2; }
[[ $# -le 3 && ( $# -lt 3 || "$3" == '--build-only' ) ]] || exit 2
mkdir -p "$probe_output"
probe_output="$(cd "$probe_output" && pwd)"
probe_source="$(cd "$(dirname "$0")" && pwd)/gr3_ble_probe.m"
probe_app="$probe_output/GR3BLEProbe.app"
[[ ! -e "$probe_app" ]] || { echo 'Use a new output directory; app already exists.' >&2; exit 2; }
mkdir -p "$probe_app/Contents/MacOS"
cat > "$probe_app/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?><plist version="1.0"><dict>
<key>CFBundleIdentifier</key><string>com.izhaoo.gr3.bleprobe</string>
<key>CFBundleName</key><string>GR3 BLE Probe</string>
<key>CFBundleExecutable</key><string>GR3BLEProbe</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>NSBluetoothAlwaysUsageDescription</key><string>只读连接理光相机，读取型号、固件、电量及对焦状态，排查裁切故障。</string>
<key>LSUIElement</key><true/>
</dict></plist>
PLIST
clang -fobjc-arc -fno-modules "$probe_source" -o "$probe_app/Contents/MacOS/GR3BLEProbe" -framework Foundation -framework AppKit -framework CoreBluetooth
codesign --force --sign - "$probe_app"
shasum -a 256 "$probe_source" "$probe_app/Contents/MacOS/GR3BLEProbe" > "$probe_output/SHA256SUMS"
if [[ "${3:-}" == '--build-only' ]]; then echo "Built: $probe_app"; exit 0; fi
# Running the app-bundled executable retains its Info.plist identity and keeps output visible.
GR3_BLE_LOG="$probe_output/events.log" GR3_BLE_SECONDS="$probe_seconds" "$probe_app/Contents/MacOS/GR3BLEProbe"
