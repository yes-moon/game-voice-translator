"""에너지 기반 음성 구간 감지.

오디오 블록 스트림을 받아서 '말소리 한 덩어리'로 잘라낸다.
조용한 구간과 아주 짧은 잡음은 버려서 효과음 노이즈를 1차로 거른다.
(faster-whisper의 vad_filter가 2차로 한 번 더 걸러준다)
"""
import numpy as np

import config


class Segmenter:
    def __init__(self, on_segment):
        self.on_segment = on_segment      # 완성된 구간(np.float32)을 넘길 콜백
        self.buf = []                     # 현재 모으는 중인 블록들
        self.in_speech = False
        self.silence_run = 0.0            # 말 시작 후 누적된 무음 길이(초)
        self.seg_len = 0.0                # 현재 구간 길이(초)

    def feed(self, block):
        rms = float(np.sqrt(np.mean(block ** 2)) + 1e-9)
        dur = len(block) / config.SAMPLE_RATE
        is_speech = rms >= config.RMS_THRESHOLD

        if is_speech:
            if not self.in_speech:
                self.in_speech = True
                self.buf = []
                self.seg_len = 0.0
            self.buf.append(block)
            self.seg_len += dur
            self.silence_run = 0.0
            if self.seg_len >= config.MAX_SEGMENT_SEC:
                self._flush()
        elif self.in_speech:
            # 말끝 여운을 조금 더 담아둔다
            self.buf.append(block)
            self.seg_len += dur
            self.silence_run += dur
            if self.silence_run >= config.SILENCE_END_SEC:
                self._flush()

    def _flush(self):
        if self.buf and self.seg_len >= config.MIN_SEGMENT_SEC:
            self.on_segment(np.concatenate(self.buf))
        self.buf = []
        self.in_speech = False
        self.silence_run = 0.0
        self.seg_len = 0.0
