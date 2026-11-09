"""AndroidManifest.xml 을 안드로이드 바이너리 XML(AXML)로 만든다.

보통은 aapt2 가 해주는 일인데, 안드로이드 SDK 없이 빌드하려고 직접 구현했다.
리소스 테이블(resources.arsc)이 없는 앱이라 문자열 값은 그대로, 시스템 리소스는 ID 로 넣는다.
"""
from __future__ import annotations

import struct
import sys

ANDROID_NS = "http://schemas.android.com/apk/res/android"

# android.R.attr 값 (android-all 14 에서 추출)
ATTR_IDS = {
    "theme": 0x01010000, "label": 0x01010001, "icon": 0x01010002, "name": 0x01010003,
    "exported": 0x01010010, "configChanges": 0x0101001F, "minSdkVersion": 0x0101020C,
    "versionCode": 0x0101021B, "versionName": 0x0101021C, "windowSoftInputMode": 0x0101022B,
    "targetSdkVersion": 0x01010270,
}

T_REF, T_STRING, T_INT, T_HEX, T_BOOL = 0x01, 0x03, 0x10, 0x11, 0x12


class Ref(int):
    """@android:... 같은 리소스 참조."""


class Hex(int):
    """플래그 값 (configChanges 등)."""


# (태그, [(android 속성인지, 이름, 값)], [자식들])
Element = tuple


def build(root: Element) -> bytes:
    # 1) 문자열 모으기: 리소스 ID 가 있는 속성 이름을 맨 앞에 (리소스 맵과 인덱스가 맞아야 함)
    attr_names: list[str] = []
    others: list[str] = []

    def walk(el):
        tag, attrs, kids = el
        others.append(tag)
        for is_android, name, val in attrs:
            if is_android:
                if name not in attr_names:
                    attr_names.append(name)
            else:
                others.append(name)
            if isinstance(val, str):
                others.append(val)
        for k in kids:
            walk(k)

    walk(root)
    others += ["android", ANDROID_NS]
    strings = list(attr_names)
    for s in others:
        if s not in strings:
            strings.append(s)
    idx = {s: i for i, s in enumerate(strings)}

    chunks = [string_pool(strings), resource_map([ATTR_IDS[n] for n in attr_names])]
    chunks.append(struct.pack("<HHIIIII", 0x0100, 16, 24, 1, 0xFFFFFFFF, idx["android"], idx[ANDROID_NS]))

    def emit(el):
        tag, attrs, kids = el
        recs = []
        for is_android, name, val in attrs:
            ns = idx[ANDROID_NS] if is_android else 0xFFFFFFFF
            if isinstance(val, bool):
                raw, typ, data = 0xFFFFFFFF, T_BOOL, 0xFFFFFFFF if val else 0
            elif isinstance(val, Ref):
                raw, typ, data = 0xFFFFFFFF, T_REF, int(val)
            elif isinstance(val, Hex):
                raw, typ, data = 0xFFFFFFFF, T_HEX, int(val)
            elif isinstance(val, int):
                raw, typ, data = 0xFFFFFFFF, T_INT, int(val)
            else:
                raw, typ, data = idx[val], T_STRING, idx[val]
            sort_key = ATTR_IDS[name] if is_android else 0xFFFFFFFF
            recs.append((sort_key, struct.pack("<IIIHBBI", ns, idx[name], raw, 8, 0, typ, data)))
        recs.sort(key=lambda r: r[0])  # 프레임워크는 속성이 리소스 ID 순으로 정렬돼 있다고 가정함
        body = struct.pack("<IIHHHHHH", 0xFFFFFFFF, idx[tag], 20, 20, len(recs), 0, 0, 0)
        body += b"".join(r[1] for r in recs)
        chunks.append(struct.pack("<HHIII", 0x0102, 16, 16 + len(body), 1, 0xFFFFFFFF) + body)
        for k in kids:
            emit(k)
        chunks.append(struct.pack("<HHIIIII", 0x0103, 16, 24, 1, 0xFFFFFFFF, 0xFFFFFFFF, idx[tag]))

    emit(root)
    chunks.append(struct.pack("<HHIIIII", 0x0101, 16, 24, 1, 0xFFFFFFFF, idx["android"], idx[ANDROID_NS]))
    payload = b"".join(chunks)
    return struct.pack("<HHI", 0x0003, 8, 8 + len(payload)) + payload


def string_pool(strings: list[str]) -> bytes:
    data = b""
    offsets = []
    for s in strings:
        offsets.append(len(data))
        enc = s.encode("utf-16-le")
        data += struct.pack("<H", len(enc) // 2) + enc + b"\x00\x00"
    data += b"\x00" * (-len(data) % 4)
    header_size = 28
    strings_start = header_size + 4 * len(strings)
    size = strings_start + len(data)
    return (struct.pack("<HHIIIIII", 0x0001, header_size, size, len(strings), 0, 0, strings_start, 0)
            + b"".join(struct.pack("<I", o) for o in offsets) + data)


def resource_map(ids: list[int]) -> bytes:
    return struct.pack("<HHI", 0x0180, 8, 8 + 4 * len(ids)) + b"".join(struct.pack("<I", i) for i in ids)


def manifest(version_code: int, version_name: str) -> Element:
    A = True
    return ("manifest", [(False, "package", "com.yeonrak.app"),
                         (A, "versionCode", version_code), (A, "versionName", version_name)], [
        ("uses-sdk", [(A, "minSdkVersion", 26), (A, "targetSdkVersion", 34)], []),
        ("uses-permission", [(A, "name", "android.permission.POST_NOTIFICATIONS")], []),
        ("uses-permission", [(A, "name", "android.permission.RECEIVE_BOOT_COMPLETED")], []),
        ("application", [(A, "label", "연락각"),
                         (A, "icon", Ref(0x01080093)),       # @android:drawable/sym_def_app_icon
                         (A, "theme", Ref(0x0103012C))], [   # @android:style/Theme.DeviceDefault.Light.NoActionBar
            ("activity", [(A, "name", ".MainActivity"), (A, "exported", True),
                          (A, "configChanges", Hex(0x4A0)),   # orientation|keyboardHidden|screenSize
                          (A, "windowSoftInputMode", Hex(0x10))], [  # adjustResize
                ("intent-filter", [], [
                    ("action", [(A, "name", "android.intent.action.MAIN")], []),
                    ("category", [(A, "name", "android.intent.category.LAUNCHER")], []),
                ]),
            ]),
            ("receiver", [(A, "name", ".ReminderReceiver"), (A, "exported", False)], [
                ("intent-filter", [], [
                    ("action", [(A, "name", "android.intent.action.BOOT_COMPLETED")], []),
                ]),
            ]),
        ]),
    ])


if __name__ == "__main__":
    out = sys.argv[1]
    code = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    name = sys.argv[3] if len(sys.argv) > 3 else "1.0"
    with open(out, "wb") as f:
        f.write(build(manifest(code, name)))
