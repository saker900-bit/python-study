#!/usr/bin/env bash
# 안드로이드 SDK 없이 APK 빌드: javac -> dx -> 직접 만든 AXML 매니페스트 -> zip -> apksig 서명
# 필요한 것: JDK 17+, python3, 인터넷(Maven Central)
set -euo pipefail
cd "$(dirname "$0")"
export JAVA_TOOL_OPTIONS="${JAVA_TOOL_OPTIONS:-}"
OUT=build; TOOLS=$OUT/tools; R=https://repo1.maven.org/maven2
mkdir -p "$TOOLS"
fetch() { [ -s "$TOOLS/$2" ] || curl -fsSL -o "$TOOLS/$2" "$R/$1"; }
fetch com/google/android/tools/dx/1.7/dx-1.7.jar dx.jar
fetch com/android/tools/build/apksig/2.3.0/apksig-2.3.0.jar apksig.jar
fetch org/robolectric/android-all/14-robolectric-10818077/android-all-14-robolectric-10818077.jar android.jar

rm -rf $OUT/classes $OUT/stage && mkdir -p $OUT/classes $OUT/stage/assets
javac -nowarn --release 8 -encoding UTF-8 -cp $TOOLS/android.jar -d $OUT/classes src/com/yeonrak/app/*.java
# dx 1.7 은 Java 6 클래스 파일까지만 읽는다. 람다 등 Java 8 문법을 안 쓰므로 버전 번호만 낮춘다.
python3 - $OUT/classes <<'PY'
import sys, pathlib
for p in pathlib.Path(sys.argv[1]).rglob("*.class"):
    b = bytearray(p.read_bytes()); b[6:8] = b"\x00\x32"; p.write_bytes(b)
PY
java -cp $TOOLS/dx.jar com.android.dx.command.Main --dex --output=$OUT/stage/classes.dex $OUT/classes
python3 tools/axml.py $OUT/stage/AndroidManifest.xml "${VERSION_CODE:-1}" "${VERSION_NAME:-1.0}"
cp assets/* $OUT/stage/assets/
(cd $OUT/stage && rm -f ../unsigned.apk && python3 -c "
import zipfile, os
with zipfile.ZipFile('../unsigned.apk', 'w', zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk('.'):
        for f in sorted(files):
            p = os.path.join(root, f); z.write(p, os.path.relpath(p, '.'))
")

KS=${KEYSTORE:-$OUT/yeonrak.p12}
if [ ! -s "$KS" ]; then
  keytool -genkeypair -keystore "$KS" -storetype PKCS12 -storepass yeonrak -keypass yeonrak -alias yeonrak \
    -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Yeonrak" >/dev/null 2>&1
fi
javac -nowarn -cp $TOOLS/apksig.jar -d $OUT/tools tools/Sign.java
# 옛 apksig 가 JDK 내부 클래스를 건드려서 export 가 필요하다
java --add-exports java.base/sun.security.x509=ALL-UNNAMED --add-exports java.base/sun.security.util=ALL-UNNAMED -cp $TOOLS/apksig.jar:$OUT/tools Sign "$KS" "${KEYSTORE_PASS:-yeonrak}" yeonrak $OUT/unsigned.apk $OUT/yeonrak.apk
