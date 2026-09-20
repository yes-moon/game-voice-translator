"""게임 음성 번역기 — 컨트롤 패널 (클릭해서 여는 GUI 프로그램).

장치/언어를 고르고 '번역 시작'을 누르면 현재 나오는 소리를 듣고
반투명 자막을 화면에 띄운다. '번역 종료'로 멈춘다.
"""
import sys

from PyQt6 import QtCore, QtGui, QtWidgets

import config
from audio_capture import list_loopback_devices
from overlay import Overlay
from pipeline import Pipeline

SOURCE_LANGS = [("en", "영어  (English)"), ("ja", "일본어  (日本語)")]
TARGET_LANGS = [("ko", "한국어"), ("en", "English"), ("ja", "日本語")]
MODELS = [("small", "빠름 (정확도 보통)"),
          ("medium", "균형 (권장)"),
          ("large-v3", "정확 (느림)")]
TRANSLATORS = [("local", "로컬 GPU (빠름·오프라인)"),
               ("google", "Google (네트워크)")]


class ControlPanel(QtWidgets.QWidget):
    # 워커 스레드 → GUI 스레드로 안전하게 넘기기 위한 시그널
    status_sig = QtCore.pyqtSignal(str)
    result_sig = QtCore.pyqtSignal(str, str, str)

    def __init__(self):
        super().__init__()
        self.overlay = None
        self.place_overlay = None
        self.pipeline = Pipeline(
            on_result=lambda o, t, s: self.result_sig.emit(o, t, s),
            on_status=lambda m: self.status_sig.emit(m))
        self._build_ui()
        self.status_sig.connect(self._on_status)
        self.result_sig.connect(self._on_result)

    # ---------- UI ----------
    def _build_ui(self):
        self.setWindowTitle("게임 음성 번역기")
        self.setMinimumWidth(420)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QtWidgets.QLabel("🎮  게임 음성 실시간 번역")
        title.setStyleSheet("font-size:18px; font-weight:bold;")
        layout.addWidget(title)

        # 캡처 장치
        layout.addWidget(self._label("소리를 잡을 장치"))
        self.device_combo = QtWidgets.QComboBox()
        self._refresh_devices()
        row = QtWidgets.QHBoxLayout()
        row.addWidget(self.device_combo, 1)
        refresh = QtWidgets.QPushButton("새로고침")
        refresh.clicked.connect(self._refresh_devices)
        row.addWidget(refresh)
        layout.addLayout(row)

        # 번역할 언어 (소스)
        layout.addWidget(self._label("번역할 언어 (들리는 언어)"))
        self.lang_checks = {}
        lang_row = QtWidgets.QHBoxLayout()
        for code, name in SOURCE_LANGS:
            cb = QtWidgets.QCheckBox(name)
            cb.setChecked(code in config.ALLOWED_LANGS)
            self.lang_checks[code] = cb
            lang_row.addWidget(cb)
        lang_row.addStretch(1)
        layout.addLayout(lang_row)

        # 목표 언어
        layout.addWidget(self._label("자막으로 보여줄 언어"))
        self.target_combo = QtWidgets.QComboBox()
        for code, name in TARGET_LANGS:
            self.target_combo.addItem(name, code)
        idx = self.target_combo.findData(config.TARGET_LANG)
        self.target_combo.setCurrentIndex(idx if idx >= 0 else 0)
        layout.addWidget(self.target_combo)

        # 음성인식 속도/정확도
        layout.addWidget(self._label("음성인식 속도 / 정확도"))
        self.model_combo = QtWidgets.QComboBox()
        for code, name in MODELS:
            self.model_combo.addItem(name, code)
        idx = self.model_combo.findData(config.MODEL_SIZE)
        self.model_combo.setCurrentIndex(idx if idx >= 0 else 1)
        layout.addWidget(self.model_combo)

        # 번역 엔진
        layout.addWidget(self._label("번역 엔진"))
        self.translator_combo = QtWidgets.QComboBox()
        for code, name in TRANSLATORS:
            self.translator_combo.addItem(name, code)
        idx = self.translator_combo.findData(config.TRANSLATOR)
        self.translator_combo.setCurrentIndex(idx if idx >= 0 else 0)
        layout.addWidget(self.translator_combo)

        # 자막 위치 잡기
        place_btn = QtWidgets.QPushButton("📍  자막 위치 잡기")
        place_btn.clicked.connect(self._place)
        layout.addWidget(place_btn)

        # 시작/종료
        self.toggle_btn = QtWidgets.QPushButton("▶  번역 시작")
        self.toggle_btn.setStyleSheet(
            "font-size:16px; font-weight:bold; padding:12px;")
        self.toggle_btn.clicked.connect(self._toggle)
        layout.addWidget(self.toggle_btn)

        # 상태 + 최근 자막
        self.status = QtWidgets.QLabel("대기 중")
        self.status.setStyleSheet("color:#666;")
        layout.addWidget(self.status)
        self.last_line = QtWidgets.QLabel("")
        self.last_line.setWordWrap(True)
        self.last_line.setStyleSheet("color:#0a6; font-size:13px;")
        layout.addWidget(self.last_line)

    def _label(self, text):
        lb = QtWidgets.QLabel(text)
        lb.setStyleSheet("font-weight:bold; margin-top:4px;")
        return lb

    def _refresh_devices(self):
        self.device_combo.clear()
        self.device_combo.addItem("기본 스피커 (자동)", None)
        try:
            for m in list_loopback_devices():
                self.device_combo.addItem(m.name, m.name)
        except Exception as e:
            self.device_combo.addItem(f"(장치 조회 실패: {e})", None)

    # ---------- 동작 ----------
    def _selected_langs(self):
        return [code for code, cb in self.lang_checks.items() if cb.isChecked()]

    def _place(self):
        # 위치 잡기 전용 오버레이 (드래그 가능)
        self.place_overlay = Overlay(placement=True)
        self.place_overlay.closed.connect(self._on_place_closed)
        self.place_overlay.show()
        self.status.setText("자막 박스를 드래그해 옮긴 뒤 Enter 를 누르면 저장됩니다.")

    def _on_place_closed(self):
        self.status.setText("자막 위치 저장됨.")
        # 이미 자막창이 떠 있으면 새 위치를 즉시 반영
        if self.overlay is not None:
            from overlay import _load_geometry
            g = _load_geometry()
            if g:
                self.overlay.setGeometry(*g)

    def _toggle(self):
        if self.pipeline.running:
            self._stop()
        else:
            self._start()

    def _start(self):
        langs = self._selected_langs()
        if not langs:
            QtWidgets.QMessageBox.warning(
                self, "언어 선택", "번역할 언어를 하나 이상 선택하세요.")
            return
        config.ALLOWED_LANGS = langs
        config.TARGET_LANG = self.target_combo.currentData()
        config.CAPTURE_DEVICE = self.device_combo.currentData()
        config.MODEL_SIZE = self.model_combo.currentData()
        config.TRANSLATOR = self.translator_combo.currentData()

        if self.overlay is None:
            self.overlay = Overlay()
        self.overlay.show()

        self._set_controls_enabled(False)
        self.toggle_btn.setText("■  번역 종료")
        self.pipeline.start()

    def _stop(self):
        self.pipeline.stop()
        if self.overlay is not None:
            self.overlay.hide()
        self._set_controls_enabled(True)
        self.toggle_btn.setText("▶  번역 시작")

    def _set_controls_enabled(self, on):
        self.device_combo.setEnabled(on)
        self.target_combo.setEnabled(on)
        self.model_combo.setEnabled(on)
        self.translator_combo.setEnabled(on)
        for cb in self.lang_checks.values():
            cb.setEnabled(on)

    # ---------- 시그널 수신 (GUI 스레드) ----------
    @QtCore.pyqtSlot(str)
    def _on_status(self, msg):
        self.status.setText(msg)

    @QtCore.pyqtSlot(str, str, str)
    def _on_result(self, original, translated, src):
        self.last_line.setText(f"[{src}] {translated}")
        if self.overlay is not None:
            self.overlay.new_subtitle.emit(original, translated, src)

    def closeEvent(self, e):
        self.pipeline.stop()
        if self.overlay is not None:
            self.overlay.close()
        if self.place_overlay is not None:
            self.place_overlay.close()
        super().closeEvent(e)


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("게임 음성 번역기")
    panel = ControlPanel()
    panel.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
