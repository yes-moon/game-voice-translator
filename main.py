"""진입점. 파이프라인을 연결하고 실행한다.

캡처 → 구간감지(VAD) → STT → 번역 → 오버레이

사용 예:
  python main.py --list-devices          # 캡처 가능한 장치 목록
  python main.py                          # 기본 스피커 소리를 한국어 자막으로
  python main.py --device Discord         # 'Discord'가 들어간 장치만 캡처
  python main.py --target en              # 영어 자막으로
  python main.py --no-overlay             # 창 없이 콘솔에만 출력
"""
import sys
import time
import argparse

from PyQt6 import QtWidgets

import config
from audio_capture import AudioCapture, list_loopback_devices
from vad_segmenter import Segmenter
from transcriber import Transcriber
from translator import Translator
from overlay import Overlay


def main():
    parser = argparse.ArgumentParser(description="게임 음성 실시간 번역 자막")
    parser.add_argument("--list-devices", action="store_true",
                        help="캡처 가능한 루프백 장치 목록 출력")
    parser.add_argument("--device", help="캡처할 장치 이름 일부 (예: Discord)")
    parser.add_argument("--target", help="목표 언어 코드 (예: ko, en, ja)")
    parser.add_argument("--no-overlay", action="store_true",
                        help="자막 창 없이 콘솔에만 출력")
    parser.add_argument("--place", action="store_true",
                        help="자막창 위치 잡기 모드: 드래그해서 옮기고 닫으면 저장")
    args = parser.parse_args()

    if args.list_devices:
        devs = list_loopback_devices()
        if not devs:
            print("루프백 장치를 찾지 못했습니다.")
        for i, m in enumerate(devs):
            print(f"[{i}] {m.name}")
        return

    if args.place:
        # 위치 잡기 모드: 오디오/STT 없이 자막창만 띄워 드래그로 배치
        app = QtWidgets.QApplication(sys.argv)
        ov = Overlay(placement=True)
        ov.show()
        print("[배치] 창을 원하는 위치로 드래그한 뒤 닫으면 저장됩니다.")
        sys.exit(app.exec())

    if args.device:
        config.CAPTURE_DEVICE = args.device
    if args.target:
        config.TARGET_LANG = args.target

    app = QtWidgets.QApplication(sys.argv)
    overlay = None if args.no_overlay else Overlay()

    def on_result(original, translated, src):
        print(f"[{src}] {original}  →  {translated}")
        if overlay:
            overlay.new_subtitle.emit(original, translated, src)

    translator = Translator(on_result)
    transcriber = Transcriber(lambda text, lang: translator.submit(text, lang))
    segmenter = Segmenter(transcriber.submit)
    capture = AudioCapture(segmenter.feed)

    translator.start()
    transcriber.start()
    capture.start()

    print(f"[준비] '{capture.device.name}' 소리를 듣는 중... "
          f"(목표 언어: {config.TARGET_LANG})")

    if overlay:
        overlay.show()
        sys.exit(app.exec())
    else:
        try:
            while True:
                app.processEvents()
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n종료합니다.")


if __name__ == "__main__":
    main()
