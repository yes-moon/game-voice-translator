"""번역 파이프라인을 시작/정지할 수 있게 묶은 컨트롤러.

GUI(control_panel)가 이걸 소유하고 start()/stop()을 호출한다.
Whisper 모델은 한 번만 로딩해 재사용하므로, 정지 후 다시 시작해도 빠르다.
콜백(on_result, on_status)은 워커 스레드에서 호출되므로,
GUI 쪽에서 반드시 Qt 시그널로 받아 메인 스레드로 넘겨야 한다.
"""
import threading

import config
from audio_capture import AudioCapture
from vad_segmenter import Segmenter
from transcriber import Transcriber
from translator import Translator


class Pipeline:
    def __init__(self, on_result, on_status):
        self.on_result = on_result      # (original, translated, src)
        self.on_status = on_status      # (message: str)
        self.model = None
        self._loaded_size = None
        self.backend = None
        self._backend_kind = None
        self.capture = None
        self.transcriber = None
        self.translator = None
        self.running = False

    def _load_model(self):
        if self.model is not None and self._loaded_size == config.MODEL_SIZE:
            return
        self.model = None   # 모델 크기가 바뀌었으면 다시 로딩
        self.on_status("모델 로딩 중... (처음엔 수십 초 걸릴 수 있어요)")
        import cuda_setup
        cuda_setup.add_cuda_dlls()
        from faster_whisper import WhisperModel
        try:
            self.model = WhisperModel(
                config.MODEL_SIZE, device=config.DEVICE,
                compute_type=config.COMPUTE_TYPE)
        except Exception as e:
            self.on_status(f"GPU 사용 불가 → CPU로 전환 ({e})")
            self.model = WhisperModel(config.MODEL_SIZE, device="cpu",
                                      compute_type="int8")
        self._loaded_size = config.MODEL_SIZE

    def _load_backend(self):
        if self.backend is not None and self._backend_kind == config.TRANSLATOR:
            return
        from translators import make_backend
        self.backend = make_backend(self.on_status)
        self._backend_kind = config.TRANSLATOR

    def start(self):
        if self.running:
            return
        self.running = True
        threading.Thread(target=self._start_bg, daemon=True).start()

    def _start_bg(self):
        try:
            self._load_model()
            self._load_backend()
        except Exception as e:
            self.on_status(f"모델 로딩 실패: {e}")
            self.running = False
            return
        if not self.running:        # 로딩 중 사용자가 정지를 눌렀으면 중단
            return

        self.translator = Translator(self.on_result, backend=self.backend)
        self.translator.start()
        self.transcriber = Transcriber(
            lambda text, lang: self.translator.submit(text, lang),
            model=self.model)
        self.transcriber.start()
        segmenter = Segmenter(self.transcriber.submit)
        try:
            self.capture = AudioCapture(segmenter.feed)
            self.capture.start()
        except Exception as e:
            self.on_status(f"오디오 장치 오류: {e}")
            self.stop()
            return
        self.on_status(f"듣는 중 — {self.capture.device.name}")

    def stop(self):
        self.running = False
        for obj in (self.capture, self.transcriber, self.translator):
            if obj is not None:
                try:
                    obj.stop()
                except Exception:
                    pass
        self.capture = self.transcriber = self.translator = None
        self.on_status("정지됨")
