"""WASAPI 루프백으로 시스템/앱 소리를 캡처해 mono float32 블록으로 흘려보낸다.

루프백 = 스피커로 '나가는' 소리를 그대로 녹음하는 것. 마이크가 아니라
컴퓨터가 재생 중인 소리(게임/디스코드 등)를 잡는다.
"""
import threading
import soundcard as sc

import config


def list_loopback_devices():
    """녹음 가능한 루프백 장치 목록."""
    mics = sc.all_microphones(include_loopback=True)
    return [m for m in mics if m.isloopback]


def _pick_device():
    """config.CAPTURE_DEVICE 기준으로 캡처할 장치를 고른다."""
    loopbacks = list_loopback_devices()

    if config.CAPTURE_DEVICE:
        for m in loopbacks:
            if config.CAPTURE_DEVICE.lower() in m.name.lower():
                return m
        raise RuntimeError(
            f"'{config.CAPTURE_DEVICE}' 와 일치하는 루프백 장치 없음. "
            f"--list-devices 로 확인하세요.")

    # 기본값: 기본 스피커의 루프백
    spk = sc.default_speaker()
    for m in loopbacks:
        if spk.name.lower() in m.name.lower() or m.name.lower() in spk.name.lower():
            return m
    if loopbacks:
        return loopbacks[0]
    raise RuntimeError("루프백 캡처 장치를 찾지 못했습니다.")


class AudioCapture(threading.Thread):
    """백그라운드 스레드: 캡처한 mono float32 블록을 on_block(np.ndarray)으로 전달."""

    def __init__(self, on_block):
        super().__init__(daemon=True)
        self.on_block = on_block
        self._stop = threading.Event()
        self.device = _pick_device()

    def run(self):
        frames = int(config.SAMPLE_RATE * config.BLOCK_SECONDS)
        with self.device.recorder(samplerate=config.SAMPLE_RATE, channels=1) as rec:
            while not self._stop.is_set():
                data = rec.record(numframes=frames)  # shape (frames, 1) float32
                self.on_block(data[:, 0].copy())

    def stop(self):
        self._stop.set()
