"""예매 사이트 서버 시각과 내 PC 시각의 차이를 재는 스크립트.

사용법:
    python server_time.py https://tickets.interpark.com
    python server_time.py https://www.letskorail.com --watch

서버는 응답 헤더(Date)에 초 단위 시각만 알려줍니다.
그래서 짧은 간격으로 계속 요청해 "초가 바뀌는 순간"을 잡아내고,
그 순간과 내 PC 시각을 비교해 약 수십 ms 정밀도로 차이를 추정합니다.
결과(초)를 모바일 도우미 화면의 '서버 시각 보정' 칸에 넣으면 됩니다.
요청은 몇 초 동안 1초에 수십 번 정도만 보내므로 서버에 부담을 주지 않습니다.
"""

import argparse
import time
import urllib.request
from email.utils import parsedate_to_datetime


def server_second(url):
    """HEAD 요청 한 번 보내고 (서버 시각 초, 요청 시작, 응답 받은 시각)을 돌려준다."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "server-time-check"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=5) as resp:
        date = resp.headers.get("Date")
    t1 = time.time()
    if not date:
        raise RuntimeError("서버가 Date 헤더를 보내지 않습니다.")
    return parsedate_to_datetime(date).timestamp(), t0, t1


def measure(url, interval=0.05, max_wait=3.0):
    """서버 시각의 초가 바뀌는 순간을 찾아 offset(서버 - 내 PC, 초)을 추정한다."""
    prev, _, _ = server_second(url)
    start = time.time()
    while time.time() - start < max_wait:
        time.sleep(interval)
        cur, t0, t1 = server_second(url)
        if cur != prev:
            # 서버의 초가 바뀐 시점은 응답 왕복 시간의 대략 중간쯤.
            local_mid = (t0 + t1) / 2
            return cur - local_mid, t1 - t0
        prev = cur
    raise RuntimeError("초가 바뀌는 순간을 찾지 못했습니다.")


def main():
    p = argparse.ArgumentParser(description="예매 사이트 서버 시각 차이 측정")
    p.add_argument("url")
    p.add_argument("-n", type=int, default=3, help="측정 횟수 (기본 3)")
    p.add_argument("--watch", action="store_true", help="보정된 서버 시각을 계속 표시")
    args = p.parse_args()

    results = []
    for i in range(args.n):
        off, rtt = measure(args.url)
        results.append(off)
        print(f"측정 {i + 1}: 차이 {off:+.3f}초 (왕복 {rtt * 1000:.0f}ms)")
    results.sort()
    offset = results[len(results) // 2]
    print(f"\n=> 서버가 내 PC보다 {offset:+.3f}초 (도우미 화면에 {offset:.3f} 입력)")

    if args.watch:
        print("Ctrl+C로 종료\n")
        try:
            while True:
                t = time.time() + offset
                ms = int((t % 1) * 1000)
                print("\r서버 시각 " + time.strftime("%H:%M:%S", time.localtime(t)) + f".{ms:03d}", end="", flush=True)
                time.sleep(0.03)
        except KeyboardInterrupt:
            print()


if __name__ == "__main__":
    main()
