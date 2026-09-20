"""반투명 · 항상 위 · 클릭 통과(click-through) 자막 오버레이.

일반 모드: 게임 위에 떠 있어도 마우스 입력을 가로채지 않음(클릭 통과).
배치 모드(--place): 드래그로 원하는 위치에 옮기고, 닫으면 위치를 저장.
저장된 위치는 다음 실행부터 자동 적용된다.
"""
import os
import json
import time

from PyQt6 import QtCore, QtGui, QtWidgets

import config

_POS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         config.POSITION_FILE)


def _load_geometry():
    """저장된 (x, y, w, h)를 반환. 없으면 None."""
    try:
        with open(_POS_PATH, "r", encoding="utf-8") as f:
            g = json.load(f)
        return int(g["x"]), int(g["y"]), int(g["w"]), int(g["h"])
    except Exception:
        return None


def _save_geometry(rect):
    with open(_POS_PATH, "w", encoding="utf-8") as f:
        json.dump({"x": rect.x(), "y": rect.y(),
                   "w": rect.width(), "h": rect.height()}, f)


class Overlay(QtWidgets.QWidget):
    new_subtitle = QtCore.pyqtSignal(str, str, str)  # (original, translated, src)
    closed = QtCore.pyqtSignal()                      # 창이 닫힐 때 (배치 모드 저장 알림)

    def __init__(self, placement=False):
        super().__init__()
        self.placement = placement      # True면 드래그로 위치 잡는 설정 모드
        self._drag_offset = None
        self.lines = []                 # [[translated, original, timestamp], ...]
        self._init_window()
        self.new_subtitle.connect(self._add)
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(500)

        if self.placement:
            # 배치 모드: 어디에 뜨는지 보이도록 예시 자막을 채워둔다
            self.lines = [
                ["① 이 박스를 드래그해서 원하는 위치로", "Drag this box", "en"],
                ["② 다 옮겼으면 Enter (저장·닫기)", "Press Enter to save", "en"],
            ]
            self.activateWindow()
            self.raise_()
            self.setFocus()

    def _init_window(self):
        flags = (QtCore.Qt.WindowType.FramelessWindowHint
                 | QtCore.Qt.WindowType.WindowStaysOnTopHint
                 | QtCore.Qt.WindowType.Tool)
        if not self.placement:
            # 일반 모드만 클릭 통과 (배치 모드에선 드래그해야 하므로 제외)
            flags |= QtCore.Qt.WindowType.WindowTransparentForInput
        self.setWindowFlags(flags)
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_TranslucentBackground)
        if not self.placement:
            # 일반 모드는 포커스를 뺏지 않게. 배치 모드는 키 입력을 받아야 함.
            self.setAttribute(QtCore.Qt.WidgetAttribute.WA_ShowWithoutActivating)

        saved = _load_geometry()
        if saved:
            x, y, w, h = saved
        else:
            screen = QtWidgets.QApplication.primaryScreen().geometry()
            w = config.OVERLAY_WIDTH
            h = config.OVERLAY_HEIGHT
            x = (screen.width() - w) // 2
            y = screen.height() - h - 80   # 기본: 하단 중앙
        self.setGeometry(x, y, w, h)

    # ---- 배치 모드: 드래그 이동 + 닫을 때 저장 ----
    def mousePressEvent(self, e):
        if self.placement and e.button() == QtCore.Qt.MouseButton.LeftButton:
            self._drag_offset = e.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, e):
        if self.placement and self._drag_offset is not None:
            self.move(e.globalPosition().toPoint() - self._drag_offset)

    def mouseReleaseEvent(self, e):
        self._drag_offset = None

    def keyPressEvent(self, e):
        # 배치 모드에서 Enter/Esc 로 닫기 (closeEvent에서 위치 저장)
        if self.placement and e.key() in (
                QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter,
                QtCore.Qt.Key.Key_Escape):
            self.close()
        else:
            super().keyPressEvent(e)

    def closeEvent(self, e):
        if self.placement:
            _save_geometry(self.geometry())
            print(f"[배치] 위치 저장됨 → {_POS_PATH}")
        self.closed.emit()
        super().closeEvent(e)

    @QtCore.pyqtSlot(str, str, str)
    def _add(self, original, translated, src):
        self.lines.append([translated, original, time.time()])
        self.lines = self.lines[-config.MAX_LINES:]
        self.update()

    def _tick(self):
        if self.placement:
            return  # 배치 모드에선 예시 자막을 유지
        now = time.time()
        before = len(self.lines)
        self.lines = [l for l in self.lines if now - l[2] < config.LINE_TTL_SEC]
        if len(self.lines) != before:
            self.update()

    def _draw_outlined(self, p, font, color, text, top, h):
        p.setFont(font)
        rect = QtCore.QRect(12, top, self.width() - 24, h)
        align = (QtCore.Qt.AlignmentFlag.AlignHCenter
                 | QtCore.Qt.AlignmentFlag.AlignVCenter)
        p.setPen(QtGui.QColor(0, 0, 0, 230))
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1),
                       (0, -1), (0, 1), (-1, 0), (1, 0)):
            p.drawText(rect.translated(dx, dy), align, text)
        p.setPen(color)
        p.drawText(rect, align, text)

    def paintEvent(self, event):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)

        # 반투명 창 잔상(고스트) 제거: 매 프레임 표면을 완전 투명으로 비운다.
        # 이게 없으면 이전 프레임 글자가 남아 새 자막과 겹쳐 보인다.
        p.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_Source)
        p.fillRect(self.rect(), QtCore.Qt.GlobalColor.transparent)
        p.setCompositionMode(QtGui.QPainter.CompositionMode.CompositionMode_SourceOver)

        if self.placement:
            # 배치 모드: 창 영역을 점선 테두리로 표시
            p.setBrush(QtGui.QColor(20, 20, 30, 90))
            pen = QtGui.QPen(QtGui.QColor(120, 200, 255, 230), 2,
                             QtCore.Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.drawRoundedRect(QtCore.QRectF(1, 1, self.width() - 2,
                                            self.height() - 2), 10, 10)

        if not self.lines:
            return

        main_font = QtGui.QFont("Malgun Gothic", config.FONT_SIZE,
                                QtGui.QFont.Weight.Bold)
        sub_font = QtGui.QFont("Malgun Gothic", int(config.FONT_SIZE * 0.6))
        mh = QtGui.QFontMetrics(main_font).height()
        sh = QtGui.QFontMetrics(sub_font).height()
        pad = 8

        y = self.height()  # 아래에서 위로 쌓는다 (최신이 맨 아래)
        for translated, original, _ in reversed(self.lines):
            show_orig = config.SHOW_ORIGINAL and original and original != translated
            block_h = mh + (sh if show_orig else 0) + pad * 2
            top = y - block_h
            rect = QtCore.QRectF(0, top, self.width(), block_h)

            p.setPen(QtCore.Qt.PenStyle.NoPen)
            p.setBrush(QtGui.QColor(0, 0, 0, 140))
            p.drawRoundedRect(rect, 10, 10)

            self._draw_outlined(p, main_font, QtGui.QColor(255, 255, 255),
                                 translated, int(top + pad), mh)
            if show_orig:
                self._draw_outlined(p, sub_font, QtGui.QColor(170, 205, 255),
                                    original, int(top + pad + mh), sh)
            y = top - 6
            if y < 0:
                break
