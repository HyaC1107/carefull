import json
import os
import socket
import sys

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QScrollArea, QScroller, QSizePolicy, QSlider, QVBoxLayout, QWidget,
)

_BG    = "#f5f6fa"
_CARD  = "white"
_DARK  = "#1e293b"
_GRAY  = "#64748b"
_GREEN = "#16a34a"
_BLUE  = "#3b82f6"
_RED   = "#dc2626"
_ORANGE = "#f97316"

_ICONS_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "assets", "icons")
)

_ICON_SIZE = 64
_CARD_PAD_H = 40
_CARD_PAD_V = 32


def _icon_label(png_name: str, fallback: str, size: int = _ICON_SIZE) -> QLabel:
    lbl = QLabel()
    lbl.setStyleSheet("background: transparent; border: none;")
    path = os.path.join(_ICONS_DIR, png_name)
    if os.path.exists(path):
        pix = QPixmap(path).scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        lbl.setPixmap(pix)
        lbl.setFixedSize(size, size)
    else:
        lbl.setText(fallback)
        lbl.setFont(QFont("Sans Serif", 22))
    return lbl


def _check_network() -> bool:
    try:
        socket.setdefaulttimeout(1)
        socket.gethostbyname("8.8.8.8")
        return True
    except Exception:
        return False


class _StatusCard(QFrame):
    def __init__(self, png_name: str, fallback_icon: str, title: str, subtitle: str, ok: bool, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"QFrame {{ background-color: {_CARD}; border-radius: 16px; }}")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(_CARD_PAD_H, _CARD_PAD_V, _CARD_PAD_H, _CARD_PAD_V)
        lay.setSpacing(20)

        lay.addWidget(_icon_label(png_name, fallback_icon))

        text_lay = QVBoxLayout()
        text_lay.setSpacing(4)

        t = QLabel(title)
        t.setFont(QFont("Sans Serif", 22, QFont.Bold))
        t.setStyleSheet(f"color: {_DARK}; background: transparent; border: none;")
        text_lay.addWidget(t)

        s = QLabel(subtitle)
        s.setFont(QFont("Sans Serif", 18))
        s.setStyleSheet(f"color: {_GRAY}; background: transparent; border: none;")
        text_lay.addWidget(s)

        lay.addLayout(text_lay)
        lay.addStretch()

        badge = QLabel("정상" if ok else "오류")
        badge.setFont(QFont("Sans Serif", 18, QFont.Bold))
        badge_color = "#dcfce7" if ok else "#fee2e2"
        badge_text = _GREEN if ok else "#dc2626"
        badge.setStyleSheet(f"""
            background-color: {badge_color};
            color: {badge_text};
            border-radius: 10px;
            padding: 6px 18px;
        """)
        lay.addWidget(badge)


class _VolumeCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"QFrame {{ background-color: {_CARD}; border-radius: 16px; }}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(_CARD_PAD_H, _CARD_PAD_V, _CARD_PAD_H, _CARD_PAD_V)
        lay.setSpacing(14)

        top = QHBoxLayout()
        top.addWidget(_icon_label("volume.png", "♪"))
        top.addSpacing(16)

        title_lbl = QLabel("알림 음량")
        title_lbl.setFont(QFont("Sans Serif", 22, QFont.Bold))
        title_lbl.setStyleSheet(f"color: {_DARK}; background: transparent; border: none;")

        self._pct_lbl = QLabel("70%")
        self._pct_lbl.setFont(QFont("Sans Serif", 22, QFont.Bold))
        self._pct_lbl.setStyleSheet(f"color: {_BLUE}; background: transparent; border: none;")

        top.addWidget(title_lbl)
        top.addStretch()
        top.addWidget(self._pct_lbl)
        lay.addLayout(top)

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setValue(70)
        self._slider.setFixedHeight(40)
        self._slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 8px;
                background: #e2e8f0;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                width: 28px;
                height: 28px;
                margin: -10px 0;
                background: {_BLUE};
                border-radius: 14px;
            }}
            QSlider::sub-page:horizontal {{
                background: {_BLUE};
                border-radius: 4px;
            }}
        """)
        self._slider.valueChanged.connect(lambda v: self._pct_lbl.setText(f"{v}%"))
        lay.addWidget(self._slider)


class _ControlCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"QFrame {{ background-color: {_CARD}; border-radius: 16px; }}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(_CARD_PAD_H, _CARD_PAD_V, _CARD_PAD_H, _CARD_PAD_V)
        lay.setSpacing(14)

        top = QHBoxLayout()
        top.addWidget(_icon_label("control.png", "⚙"))
        top.addSpacing(16)

        title_lbl = QLabel("기기 제어")
        title_lbl.setFont(QFont("Sans Serif", 22, QFont.Bold))
        title_lbl.setStyleSheet(f"color: {_DARK}; background: transparent; border: none;")
        top.addWidget(title_lbl)
        top.addStretch()
        lay.addLayout(top)

        restart_btn = QPushButton("재시작")
        restart_btn.setMinimumHeight(80)
        restart_btn.setFont(QFont("Sans Serif", 24, QFont.Bold))
        restart_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #fff3e0;
                color: {_ORANGE};
                border: 2px solid #fed7aa;
                border-radius: 16px;
            }}
            QPushButton:pressed {{ background-color: #ffe0b2; }}
        """)
        restart_btn.clicked.connect(self._restart)
        lay.addWidget(restart_btn)

        exit_btn = QPushButton("앱 종료")
        exit_btn.setMinimumHeight(80)
        exit_btn.setFont(QFont("Sans Serif", 24, QFont.Bold))
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #fee2e2;
                color: #dc2626;
                border: 2px solid #fca5a5;
                border-radius: 16px;
            }
            QPushButton:pressed { background-color: #fecaca; }
        """)
        exit_btn.clicked.connect(self._exit)
        lay.addWidget(exit_btn)

    @staticmethod
    def _restart():
        try:
            os.system("sudo reboot")
        except Exception:
            pass

    @staticmethod
    def _exit():
        # pm2 stop으로 종료해야 PM2가 의도적 종료로 인식해 재시작하지 않음
        ret = os.system("pm2 stop carefull")
        if ret != 0:
            # pm2가 없는 환경(직접 실행 등)이면 그냥 종료
            QApplication.quit()


_DB_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "db", "user_db.json")
)


class _FaceDeleteWorker(QThread):
    done = pyqtSignal(bool)

    def run(self):
        server_ok = False
        try:
            from api.client import delete_face_embedding
            server_ok = delete_face_embedding()
        except Exception as e:
            print(f"[FACE DELETE] server: {e}")

        try:
            with open(_DB_PATH, "w", encoding="utf-8") as f:
                json.dump({}, f)
        except Exception as e:
            print(f"[FACE DELETE] local: {e}")

        try:
            from auth.authenticate import invalidate_embedding_cache
            invalidate_embedding_cache()
        except Exception:
            pass

        self.done.emit(server_ok)


class _FaceCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self.setStyleSheet(f"QFrame {{ background-color: {_CARD}; border-radius: 16px; }}")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(_CARD_PAD_H, _CARD_PAD_V, _CARD_PAD_H, _CARD_PAD_V)
        outer.setSpacing(12)

        header = QHBoxLayout()
        header.addWidget(_icon_label("face.png", "👤"))
        header.addSpacing(12)

        title = QLabel("사용자 얼굴")
        title.setFont(QFont("Sans Serif", 22, QFont.Bold))
        title.setStyleSheet(f"color: {_DARK}; background: transparent; border: none;")
        header.addWidget(title)
        header.addStretch()

        self._badge = QLabel()
        self._badge.setFont(QFont("Sans Serif", 18, QFont.Bold))
        header.addWidget(self._badge)
        outer.addLayout(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #e2e8f0;")
        outer.addWidget(sep)

        self._del_btn = QPushButton("등록된 사용자 삭제")
        self._del_btn.setMinimumHeight(80)
        self._del_btn.setFont(QFont("Sans Serif", 22, QFont.Bold))
        self._del_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #fee2e2;
                color: {_RED};
                border: 2px solid #fca5a5;
                border-radius: 16px;
            }}
            QPushButton:pressed {{ background-color: #fecaca; }}
            QPushButton:disabled {{
                background-color: #f1f5f9;
                color: #94a3b8;
                border-color: #e2e8f0;
            }}
        """)
        self._del_btn.clicked.connect(self._on_delete_clicked)
        outer.addWidget(self._del_btn)

        self.refresh()

    def _has_face(self) -> bool:
        try:
            with open(_DB_PATH, "r", encoding="utf-8") as f:
                return bool(json.load(f))
        except Exception:
            return False

    def refresh(self):
        has = self._has_face()
        if has:
            self._badge.setText("등록됨")
            self._badge.setStyleSheet(
                f"background: #dcfce7; color: {_GREEN}; border-radius: 10px; padding: 6px 18px;"
            )
        else:
            self._badge.setText("미등록")
            self._badge.setStyleSheet(
                "background: #e2e8f0; color: #64748b; border-radius: 10px; padding: 6px 18px;"
            )
        self._del_btn.setEnabled(has)

    def _on_delete_clicked(self):
        box = QMessageBox(self)
        box.setWindowTitle("사용자 삭제")
        box.setText("등록된 사용자 얼굴 정보를\n모두 삭제하시겠습니까?")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)
        box.button(QMessageBox.Yes).setText("삭제")
        box.button(QMessageBox.No).setText("취소")
        box.setStyleSheet("""
            QMessageBox { background: white; }
            QLabel { font-size: 22px; color: #1e293b; }
            QPushButton { min-height: 60px; min-width: 110px; font-size: 20px; border-radius: 10px; }
        """)
        if box.exec_() != QMessageBox.Yes:
            return

        self._del_btn.setEnabled(False)
        self._del_btn.setText("삭제 중...")
        self._worker = _FaceDeleteWorker(parent=self)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _on_done(self, _server_ok: bool):
        self._del_btn.setText("등록된 사용자 삭제")
        self.refresh()


class _FingerprintFetchWorker(QThread):
    done = pyqtSignal(list)

    def run(self):
        try:
            from api.client import fetch_fingerprints
            fps = fetch_fingerprints()
        except Exception:
            fps = []
        self.done.emit(fps)


class _FingerprintDeleteWorker(QThread):
    done = pyqtSignal()

    def __init__(self, slot_id: int, parent=None):
        super().__init__(parent)
        self._slot_id = slot_id

    def run(self):
        try:
            from api.client import delete_fingerprint
            delete_fingerprint(self._slot_id)
        except Exception as e:
            print(f"[FP DELETE SERVER ERROR] {e}")
        try:
            from hardware.fingerprint import get_fingerprint_manager
            get_fingerprint_manager().delete_template(self._slot_id)
        except Exception as e:
            print(f"[FP DELETE HW ERROR] {e}")
        self.done.emit()


class _FingerprintCard(QFrame):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self._app = app
        self._workers = []
        self.setStyleSheet(f"QFrame {{ background-color: {_CARD}; border-radius: 16px; }}")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(_CARD_PAD_H, _CARD_PAD_V, _CARD_PAD_H, _CARD_PAD_V)
        outer.setSpacing(12)

        # 헤더 행
        header = QHBoxLayout()
        header.addWidget(_icon_label("fingerprint.png", "🔒"))
        header.addSpacing(12)

        title = QLabel("지문 관리")
        title.setFont(QFont("Sans Serif", 22, QFont.Bold))
        title.setStyleSheet(f"color: {_DARK}; background: transparent; border: none;")
        header.addWidget(title)
        header.addStretch()

        add_btn = QPushButton("추가 등록")
        add_btn.setFont(QFont("Sans Serif", 18, QFont.Bold))
        add_btn.setFixedHeight(48)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {_BLUE};
                color: white;
                border-radius: 10px;
                padding: 0 18px;
                border: none;
            }}
            QPushButton:pressed {{ background-color: #2563eb; }}
        """)
        add_btn.clicked.connect(self._on_add)
        header.addWidget(add_btn)
        outer.addLayout(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #e2e8f0;")
        outer.addWidget(sep)

        self._list_container = QWidget()
        self._list_container.setStyleSheet("background: transparent;")
        self._list_lay = QVBoxLayout(self._list_container)
        self._list_lay.setContentsMargins(0, 0, 0, 0)
        self._list_lay.setSpacing(8)
        outer.addWidget(self._list_container)

        self._status_lbl = QLabel("불러오는 중...")
        self._status_lbl.setFont(QFont("Sans Serif", 18))
        self._status_lbl.setAlignment(Qt.AlignCenter)
        self._status_lbl.setStyleSheet(f"color: {_GRAY}; background: transparent; border: none;")
        self._list_lay.addWidget(self._status_lbl)

    def refresh(self):
        self._status_lbl.setText("불러오는 중...")
        self._clear_rows()
        self._list_lay.addWidget(self._status_lbl)
        self._status_lbl.show()

        worker = _FingerprintFetchWorker(parent=self)
        worker.done.connect(self._on_fetched)
        self._workers.append(worker)
        worker.start()

    def _clear_rows(self):
        while self._list_lay.count():
            item = self._list_lay.takeAt(0)
            w = item.widget()
            if w and w is not self._status_lbl:
                w.deleteLater()

    def _on_fetched(self, fingerprints: list):
        self._clear_rows()
        if not fingerprints:
            self._status_lbl.setText("등록된 지문이 없습니다")
            self._list_lay.addWidget(self._status_lbl)
            self._status_lbl.show()
            return
        self._status_lbl.hide()
        for fp in fingerprints:
            self._list_lay.addWidget(self._make_row(fp))

    def _make_row(self, fp: dict) -> QWidget:
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(0, 4, 0, 4)
        lay.setSpacing(12)

        badge = QLabel(str(fp["slot_id"]))
        badge.setFont(QFont("Sans Serif", 18, QFont.Bold))
        badge.setFixedSize(40, 40)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(f"background: {_BLUE}; color: white; border-radius: 20px;")
        lay.addWidget(badge)

        name_lbl = QLabel(fp.get("label", "지문"))
        name_lbl.setFont(QFont("Sans Serif", 20))
        name_lbl.setStyleSheet(f"color: {_DARK}; background: transparent; border: none;")
        lay.addWidget(name_lbl)

        if fp.get("registered_at"):
            date_lbl = QLabel(str(fp["registered_at"])[:10])
            date_lbl.setFont(QFont("Sans Serif", 18))
            date_lbl.setStyleSheet(f"color: {_GRAY}; background: transparent; border: none;")
            lay.addWidget(date_lbl)

        lay.addStretch()

        del_btn = QPushButton("삭제")
        del_btn.setFont(QFont("Sans Serif", 18))
        del_btn.setFixedHeight(48)
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: #fee2e2;
                color: {_RED};
                border: 1.5px solid #fca5a5;
                border-radius: 8px;
                padding: 0 14px;
            }}
            QPushButton:pressed {{ background: #fecaca; }}
        """)
        slot_id = fp["slot_id"]
        del_btn.clicked.connect(lambda _, s=slot_id: self._on_delete(s))
        lay.addWidget(del_btn)
        return row

    def _on_add(self):
        if self._app:
            self._app.show_screen("fingerprint_register")

    def _on_delete(self, slot_id: int):
        worker = _FingerprintDeleteWorker(slot_id, parent=self)
        worker.done.connect(self.refresh)
        self._workers.append(worker)
        worker.start()


class SettingsScreen(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._app = parent
        self._fp_card = None
        self._face_card = None
        self._build_ui()

    def showEvent(self, event):
        super().showEvent(event)
        if self._face_card:
            self._face_card.refresh()
        if self._fp_card:
            self._fp_card.refresh()

    def _build_ui(self):
        self.setStyleSheet(f"SettingsScreen {{ background-color: {_BG}; }}")
        root = QVBoxLayout(self)
        root.setContentsMargins(80, 24, 80, 24)
        root.setSpacing(0)

        # 상단 헤더
        header = QHBoxLayout()
        back_btn = QPushButton("← 메인으로")
        back_btn.setFont(QFont("Sans Serif", 22))
        back_btn.setFixedHeight(64)
        back_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        back_btn.setStyleSheet("""
            QPushButton {
                background: white;
                color: #374151;
                border: 2px solid #d0d5dd;
                border-radius: 14px;
                padding: 4px 24px;
            }
            QPushButton:pressed { background: #f0f0f0; }
        """)
        back_btn.clicked.connect(lambda: self._app.show_screen("home"))

        title = QLabel("설정")
        title.setFont(QFont("Sans Serif", 28, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: {_DARK};")

        spacer = QWidget()
        spacer.setFixedWidth(back_btn.sizeHint().width())

        header.addWidget(back_btn)
        header.addStretch()
        header.addWidget(title)
        header.addStretch()
        header.addWidget(spacer)
        root.addLayout(header)

        root.addSpacing(14)

        # 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("background: transparent;")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        QScroller.grabGesture(scroll.viewport(), QScroller.LeftMouseButtonGesture)

        content = QWidget()
        content.setStyleSheet("background: transparent;")
        c_lay = QVBoxLayout(content)
        c_lay.setSpacing(14)
        c_lay.setContentsMargins(0, 0, 0, 0)

        wifi_ok = _check_network()
        c_lay.addWidget(_StatusCard("wifi.png", "WiFi", "WiFi 연결", "연결됨" if wifi_ok else "연결 안됨", wifi_ok))
        c_lay.addWidget(_StatusCard("server.png", "서버", "서버 통신", "통신 가능", True))
        c_lay.addWidget(_VolumeCard())

        self._face_card = _FaceCard()
        c_lay.addWidget(self._face_card)

        self._fp_card = _FingerprintCard(self._app)
        c_lay.addWidget(self._fp_card)

        c_lay.addWidget(_ControlCard())
        c_lay.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

        root.addSpacing(8)

        ver = QLabel("Smart Medication Dispenser v1.0")
        ver.setFont(QFont("Sans Serif", 16))
        ver.setAlignment(Qt.AlignCenter)
        ver.setStyleSheet(f"color: {_GRAY};")
        root.addWidget(ver)
