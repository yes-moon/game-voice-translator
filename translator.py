"""번역 워커 스레드.

실제 번역은 translators.py의 백엔드(로컬 GPU/NLLB 또는 Google)가 담당한다.
백엔드를 외부에서 주입할 수 있고, 없으면 스레드 시작 시 생성한다.
"""
import threading
import queue

import config
from glossary import normalize_source, fix_target


class Translator(threading.Thread):
    def __init__(self, on_result, backend=None):
        super().__init__(daemon=True)
        self.on_result = on_result        # on_result(original, translated, src_lang)
        self.backend = backend
        self.q = queue.Queue()
        self._stop = threading.Event()

    def submit(self, text, src_lang):
        self.q.put((text, src_lang))

    def run(self):
        if self.backend is None:
            from translators import make_backend
            self.backend = make_backend()

        while not self._stop.is_set():
            try:
                text, src = self.q.get(timeout=0.2)
            except queue.Empty:
                continue

            # 이미 목표 언어면 번역 생략
            if src == config.TARGET_LANG:
                self.on_result(text, text, src)
                continue

            try:
                src_text = normalize_source(text, src) if config.USE_GLOSSARY else text
                translated = self.backend.translate(src_text, src, config.TARGET_LANG)
                if config.USE_GLOSSARY:
                    translated = fix_target(translated)
            except Exception as e:
                print(f"[번역] 오류: {e}")
                translated = text
            # 화면 원문은 보정 전 '진짜 원문'을 보여준다
            self.on_result(text, translated or text, src)

    def stop(self):
        self._stop.set()
