"""faster-whisper 음성인식을 워커 스레드에서 돌린다.

GPU 로딩 실패 시 자동으로 CPU(int8)로 폴백한다.
"""
import threading
import queue

import config
import cuda_setup

cuda_setup.add_cuda_dlls()  # faster_whisper import 전에 CUDA DLL 경로 등록


class Transcriber(threading.Thread):
    def __init__(self, on_text, model=None):
        super().__init__(daemon=True)
        self.on_text = on_text            # on_text(text:str, lang:str)
        self.q = queue.Queue()
        self._stop = threading.Event()
        self.model = model                # 미리 로딩한 모델을 받으면 재사용

    def submit(self, segment):
        # 큐가 밀리면 오래된 구간을 버려서 자막 지연이 누적되지 않게 한다
        while self.q.qsize() >= config.MAX_PENDING_SEGMENTS:
            try:
                self.q.get_nowait()
            except queue.Empty:
                break
        self.q.put(segment)

    def run(self):
        if self.model is None:
            from faster_whisper import WhisperModel
            try:
                self.model = WhisperModel(
                    config.MODEL_SIZE, device=config.DEVICE,
                    compute_type=config.COMPUTE_TYPE)
                print(f"[STT] {config.MODEL_SIZE} on {config.DEVICE} 준비 완료")
            except Exception as e:
                print(f"[STT] GPU 로딩 실패({e}) → CPU int8로 폴백")
                self.model = WhisperModel(config.MODEL_SIZE, device="cpu",
                                          compute_type="int8")
                print(f"[STT] {config.MODEL_SIZE} on cpu 준비 완료")

        while not self._stop.is_set():
            try:
                seg = self.q.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                text, lang = self._transcribe(seg)
            except Exception as e:
                print(f"[STT] 인식 오류: {e}")
                continue
            if text and lang:
                self.on_text(text, lang)

    def _opts(self):
        # 노이즈에서 헛듣고(hallucination) 엉뚱한 문장을 지어내는 걸 줄이는 옵션
        return dict(
            vad_filter=True,
            beam_size=config.DECODE_BEAM,       # 클수록 정확 (노이즈에 강함)
            condition_on_previous_text=False,   # 반복/이어쓰기 폭주 방지
            no_speech_threshold=0.6,            # 무음일 확률 높으면 버림
            log_prob_threshold=-1.0,            # 확신 낮은 결과 버림
            compression_ratio_threshold=2.4,    # 같은 말 반복(환청) 버림
        )

    def _join(self, segments):
        """확신 낮은(=노이즈일 가능성 높은) 구간은 버리고 합친다."""
        parts = []
        for s in segments:
            if getattr(s, "no_speech_prob", 0.0) > 0.6:
                continue
            if getattr(s, "avg_logprob", 0.0) < -1.0:
                continue
            t = s.text.strip()
            if t:
                parts.append(t)
        return " ".join(parts).strip()

    def _transcribe(self, seg):
        """(text, lang) 반환. 영어/일본어가 아니면 (None, None)으로 건너뜀.

        자동감지 한 번만 수행한다. 엉뚱한 언어로 강제 재디코딩하지 않는다
        (그게 노이즈에서 헛소리를 만들던 원인).
        """
        # config에서 언어를 하드코딩으로 고정한 경우에만 강제
        if config.SOURCE_LANG:
            segs, _ = self.model.transcribe(
                seg, language=config.SOURCE_LANG, **self._opts())
            return self._join(segs), config.SOURCE_LANG

        segs, info = self.model.transcribe(seg, language=None, **self._opts())
        # 감지된 언어가 영/일이 아니거나 확신이 낮으면(노이즈/한국어 등) 무시
        if (info.language not in config.ALLOWED_LANGS
                or info.language_probability < config.MIN_LANG_PROB):
            return None, None
        return self._join(segs), info.language

    def stop(self):
        self._stop.set()
