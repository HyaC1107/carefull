import json
import os
import re
import socket
import subprocess
import sys

from PyQt5.QtCore import Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QScrollArea, QScroller, QSizePolicy, QSlider, QVBoxLayout, QWidget,
)

from utils.ui_prefs import FONT_SCALE as _FS

def _fs(n: int) -> int:
    return max(1, int(n * _FS))

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

_KW, _KH = 62, 44   # 온스크린 키보드 키 크기


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


def _signal_icon(signal: int) -> str:
    if signal >= 75: return "▂▄▆█"
    if signal >= 50: return "▂▄▆·"
    if signal >= 25: return "▂▄··"
    return "▂···"


def _current_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(1)
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        pass
    return "IP 없음"


def _current_ssid() -> str:
    try:
        out = subprocess.check_output(
            ["nmcli", "-t", "-f", "TYPE,NAME", "con", "show", "--active"],
            text=True, timeout=5, stderr=subprocess.DEVNULL,
        )
        for line in out.strip().splitlines():
            parts = line.split(":", 1)
            if len(parts) >= 2 and parts[0] == "802-11-wireless":
                return parts[1].strip()
    except Exception:
        pass
    return "연결 안됨"


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
        self.setStyleSheet(f"QFrame {{ background-color: {_CARD}; border-radius: {_fs(16)}px; }}")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(_fs(_CARD_PAD_H), _fs(_CARD_PAD_V), _fs(_CARD_PAD_H), _fs(_CARD_PAD_V))
        lay.setSpacing(_fs(20))

        lay.addWidget(_icon_label(png_name, fallback_icon, size=_fs(_ICON_SIZE)))

        text_lay = QVBoxLayout()
        text_lay.setSpacing(_fs(4))

        t = QLabel(title)
        t.setFont(QFont("Sans Serif", _fs(22), QFont.Bold))
        t.setStyleSheet(f"color: {_DARK}; background: transparent; border: none;")
        text_lay.addWidget(t)

        s = QLabel(subtitle)
        s.setFont(QFont("Sans Serif", _fs(18)))
        s.setStyleSheet(f"color: {_GRAY}; background: transparent; border: none;")
        text_lay.addWidget(s)

        lay.addLayout(text_lay)
        lay.addStretch()

        badge = QLabel("정상" if ok else "오류")
        badge.setFont(QFont("Sans Serif", _fs(18), QFont.Bold))
        badge_color = "#dcfce7" if ok else "#fee2e2"
        badge_text = _GREEN if ok else "#dc2626"
        badge.setStyleSheet(f"""
            background-color: {badge_color};
            color: {badge_text};
            border-radius: {_fs(10)}px;
            padding: {_fs(6)}px {_fs(18)}px;
        """)
        lay.addWidget(badge)


class _WifiScanThread(QThread):
    done = pyqtSignal(list)

    def run(self):
        try:
            subprocess.run(["sudo", "nmcli", "dev", "wifi", "rescan"],
                           capture_output=True, timeout=8)
        except Exception:
            pass
        try:
            out = subprocess.check_output(
                ["nmcli", "-g", "IN-USE,SSID,SIGNAL,SECURITY", "dev", "wifi", "list"],
                text=True, timeout=10, stderr=subprocess.DEVNULL,
            )
            networks, seen = [], set()
            for line in out.strip().splitlines():
                parts = re.split(r'(?<!\\):', line)
                if len(parts) < 3:
                    continue
                in_use = parts[0].strip() == "*"
                ssid   = parts[1].replace("\\:", ":").strip()
                if not ssid or ssid in seen:
                    continue
                seen.add(ssid)
                try:    signal = int(parts[2].strip())
                except: signal = 0
                secured = len(parts) > 3 and bool(parts[3].strip())
                networks.append({"ssid": ssid, "signal": signal,
                                  "secured": secured, "connected": in_use})
            networks.sort(key=lambda x: (-int(x["connected"]), -x["signal"]))
            self.done.emit(networks)
        except Exception as e:
            print(f"[WIFI SCAN] {e}")
            self.done.emit([])


class _WifiConnectThread(QThread):
    success = pyqtSignal(str)
    failed  = pyqtSignal(str)

    def __init__(self, ssid: str, password: str = "", parent=None):
        super().__init__(parent)
        self._ssid, self._password = ssid, password

    def run(self):
        try:
            if self._password:
                cmd = ["sudo", "nmcli", "dev", "wifi", "connect",
                       self._ssid, "password", self._password]
            else:
                r = subprocess.run(["sudo", "nmcli", "con", "up", self._ssid],
                                   capture_output=True, text=True, timeout=30)
                if r.returncode == 0:
                    self.success.emit(self._ssid)
                    return
                cmd = ["sudo", "nmcli", "dev", "wifi", "connect", self._ssid]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                self.success.emit(self._ssid)
            else:
                self.failed.emit((r.stderr or r.stdout or "연결 실패").strip()[:60])
        except subprocess.TimeoutExpired:
            self.failed.emit("연결 시간 초과")
        except Exception as e:
            self.failed.emit(str(e)[:60])


class _WifiPasswordDialog(QDialog):
    """터치 전용 온스크린 키보드로 WiFi 비밀번호 입력."""
    _ROWS     = ["1234567890", "qwertyuiop", "asdfghjkl", "zxcvbnm"]
    _SPECIALS = ["-", "_", ".", "@", "!"]

    def __init__(self, ssid: str, parent=None):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.setModal(True)
        self.setFixedSize(740, 496)
        self.setStyleSheet("QDialog { background: #1e293b; border-radius: 20px; }")
        self._pw      = ""
        self._shifted = False
        self._build_ui(ssid)

    def get_password(self) -> str:
        return self._pw

    def _build_ui(self, ssid: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 14, 18, 14)
        root.setSpacing(6)

        title = QLabel(f"'{ssid}' 비밀번호 입력")
        title.setFont(QFont("Sans Serif", 19, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: white; background: transparent;")
        root.addWidget(title)

        self._display = QLabel("")
        self._display.setFont(QFont("Monospace", 20, QFont.Bold))
        self._display.setAlignment(Qt.AlignCenter)
        self._display.setFixedHeight(48)
        self._display.setStyleSheet("""
            background: #334155; border: 2px solid #475569;
            border-radius: 10px; color: white;
            padding: 4px 16px; letter-spacing: 6px;
        """)
        root.addWidget(self._display)

        _KSS = """
            QPushButton { background: #475569; border: none;
                          border-radius: 6px; color: white; }
            QPushButton:pressed { background: #64748b; }
        """

        for row_str in self._ROWS:
            rw = QWidget()
            rw.setStyleSheet("background: transparent;")
            rl = QHBoxLayout(rw)
            rl.setSpacing(3)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.addStretch()
            for ch in row_str:
                b = QPushButton(ch)
                b.setFixedSize(_KW, _KH)
                b.setFont(QFont("Sans Serif", 14, QFont.Bold))
                b.setStyleSheet(_KSS)
                b.clicked.connect(lambda _, c=ch: self._press(c))
                rl.addWidget(b)
            rl.addStretch()
            root.addWidget(rw)

        # 제어 행: ⇧ | Space | 특수문자 | ⌫
        ctrl_w = QWidget()
        ctrl_w.setStyleSheet("background: transparent;")
        ctrl_l = QHBoxLayout(ctrl_w)
        ctrl_l.setSpacing(4)
        ctrl_l.setContentsMargins(0, 0, 0, 0)
        ctrl_l.addStretch()

        self._shift_btn = QPushButton("⇧")
        self._shift_btn.setFixedSize(76, _KH)
        self._shift_btn.setFont(QFont("Sans Serif", 16, QFont.Bold))
        self._shift_btn.setCheckable(True)
        self._shift_btn.setStyleSheet("""
            QPushButton         { background: #475569; border: none; border-radius: 6px; color: white; }
            QPushButton:checked { background: #3b82f6; }
            QPushButton:pressed { background: #64748b; }
        """)
        self._shift_btn.clicked.connect(lambda checked: setattr(self, "_shifted", checked))
        ctrl_l.addWidget(self._shift_btn)

        space_btn = QPushButton("Space")
        space_btn.setFixedHeight(_KH)
        space_btn.setFixedWidth(170)
        space_btn.setFont(QFont("Sans Serif", 13))
        space_btn.setStyleSheet(_KSS)
        space_btn.clicked.connect(lambda: self._press(" "))
        ctrl_l.addWidget(space_btn)

        for sp in self._SPECIALS:
            b = QPushButton(sp)
            b.setFixedSize(52, _KH)
            b.setFont(QFont("Sans Serif", 15, QFont.Bold))
            b.setStyleSheet(_KSS)
            b.clicked.connect(lambda _, c=sp: self._press(c))
            ctrl_l.addWidget(b)

        del_btn = QPushButton("⌫")
        del_btn.setFixedSize(76, _KH)
        del_btn.setFont(QFont("Sans Serif", 18))
        del_btn.setStyleSheet("""
            QPushButton { background: #dc2626; border: none; border-radius: 6px; color: white; }
            QPushButton:pressed { background: #b91c1c; }
        """)
        del_btn.clicked.connect(self._backspace)
        ctrl_l.addWidget(del_btn)

        ctrl_l.addStretch()
        root.addWidget(ctrl_w)

        # 확인/취소 행
        act_w = QWidget()
        act_w.setStyleSheet("background: transparent;")
        act_l = QHBoxLayout(act_w)
        act_l.setSpacing(12)
        act_l.setContentsMargins(0, 4, 0, 0)

        cancel_btn = QPushButton("취소")
        cancel_btn.setFixedHeight(52)
        cancel_btn.setFont(QFont("Sans Serif", 18, QFont.Bold))
        cancel_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        cancel_btn.setStyleSheet("""
            QPushButton { background: #334155; color: #94a3b8;
                          border: 2px solid #475569; border-radius: 12px; }
            QPushButton:pressed { background: #475569; }
        """)
        cancel_btn.clicked.connect(self.reject)
        act_l.addWidget(cancel_btn)

        ok_btn = QPushButton("연결")
        ok_btn.setFixedHeight(52)
        ok_btn.setFont(QFont("Sans Serif", 18, QFont.Bold))
        ok_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        ok_btn.setStyleSheet("""
            QPushButton { background: #3b82f6; color: white;
                          border: none; border-radius: 12px; }
            QPushButton:pressed { background: #2563eb; }
        """)
        ok_btn.clicked.connect(self.accept)
        act_l.addWidget(ok_btn)

        root.addWidget(act_w)

    def _press(self, ch: str):
        c = ch.upper() if (self._shifted and ch.isalpha()) else ch
        self._pw += c
        if self._shifted and ch.isalpha():
            self._shifted = False
            self._shift_btn.setChecked(False)
        self._display.setText("●" * len(self._pw))

    def _backspace(self):
        self._pw = self._pw[:-1]
        self._display.setText("●" * len(self._pw))

    def exec_centered(self, parent_geom):
        x = parent_geom.x() + (parent_geom.width()  - self.width())  // 2
        y = parent_geom.y() + (parent_geom.height() - self.height()) // 2
        self.move(x, y)
        return self.exec_()


class _WifiCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._scan_thread    = None
        self._connect_thread = None
        self.setStyleSheet(f"QFrame {{ background-color: {_CARD}; border-radius: {_fs(16)}px; }}")

        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(_fs(_CARD_PAD_H), _fs(_CARD_PAD_V), _fs(_CARD_PAD_H), _fs(_CARD_PAD_V))
        self._outer.setSpacing(_fs(12))

        # 헤더
        hdr = QHBoxLayout()
        hdr.addWidget(_icon_label("wifi.png", "WiFi", size=_fs(_ICON_SIZE)))
        hdr.addSpacing(_fs(12))

        info = QVBoxLayout()
        info.setSpacing(_fs(2))
        title_lbl = QLabel("와이파이")
        title_lbl.setFont(QFont("Sans Serif", _fs(22), QFont.Bold))
        title_lbl.setStyleSheet(f"color: {_DARK}; background: transparent; border: none;")
        info.addWidget(title_lbl)
        self._ssid_lbl = QLabel(_current_ssid())
        self._ssid_lbl.setFont(QFont("Sans Serif", _fs(18)))
        self._ssid_lbl.setStyleSheet(f"color: {_GRAY}; background: transparent; border: none;")
        info.addWidget(self._ssid_lbl)

        self._ip_lbl = QLabel(_current_ip())
        self._ip_lbl.setFont(QFont("Monospace", _fs(17)))
        self._ip_lbl.setStyleSheet(f"color: {_BLUE}; background: transparent; border: none;")
        info.addWidget(self._ip_lbl)

        hdr.addLayout(info)
        hdr.addStretch()

        self._change_btn = QPushButton("네트워크 변경")
        self._change_btn.setFont(QFont("Sans Serif", _fs(18), QFont.Bold))
        self._change_btn.setFixedHeight(_fs(52))
        self._change_btn.setStyleSheet(f"""
            QPushButton {{ background: {_BLUE}; color: white;
                           border-radius: {_fs(10)}px; padding: 0 {_fs(18)}px; border: none; }}
            QPushButton:pressed {{ background: #2563eb; }}
        """)
        self._change_btn.clicked.connect(self._on_scan)
        hdr.addWidget(self._change_btn)
        self._outer.addLayout(hdr)

        # 상태 레이블
        self._status_lbl = QLabel("")
        self._status_lbl.setFont(QFont("Sans Serif", _fs(18)))
        self._status_lbl.setAlignment(Qt.AlignCenter)
        self._status_lbl.setStyleSheet(f"color: {_GRAY}; background: transparent; border: none;")
        self._status_lbl.hide()
        self._outer.addWidget(self._status_lbl)

        # 네트워크 목록 (스캔 후 표시)
        self._list_widget = QWidget()
        self._list_widget.setStyleSheet("background: transparent;")
        self._list_lay = QVBoxLayout(self._list_widget)
        self._list_lay.setContentsMargins(0, 0, 0, 0)
        self._list_lay.setSpacing(_fs(6))
        self._list_widget.hide()
        self._outer.addWidget(self._list_widget)

    def _on_scan(self):
        if self._list_widget.isVisible():
            self._list_widget.hide()
            self._status_lbl.hide()
            self._change_btn.setText("네트워크 변경")
            return
        self._change_btn.setEnabled(False)
        self._set_status("네트워크 검색 중...", _GRAY)
        self._scan_thread = _WifiScanThread(parent=self)
        self._scan_thread.done.connect(self._on_scanned)
        self._scan_thread.start()

    def _on_scanned(self, networks: list):
        self._change_btn.setEnabled(True)
        self._status_lbl.hide()

        while self._list_lay.count():
            item = self._list_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not networks:
            self._set_status("검색된 네트워크가 없습니다", _GRAY)
            return

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #e2e8f0;")
        self._list_lay.addWidget(sep)

        for net in networks:
            self._list_lay.addWidget(self._make_row(net))
        self._list_widget.show()
        self._change_btn.setText("닫기")

    def _make_row(self, net: dict) -> QWidget:
        row = QWidget()
        row.setStyleSheet(f"""
            QWidget {{ background: {"#eff6ff" if net["connected"] else "#f8fafc"};
                      border-radius: {_fs(10)}px; }}
        """)
        rl = QHBoxLayout(row)
        rl.setContentsMargins(_fs(12), _fs(8), _fs(12), _fs(8))
        rl.setSpacing(_fs(10))

        sig_lbl = QLabel(_signal_icon(net["signal"]))
        sig_lbl.setFont(QFont("Monospace", _fs(14)))
        sig_lbl.setFixedWidth(_fs(52))
        sig_lbl.setStyleSheet("background: transparent; color: #64748b; border: none;")
        rl.addWidget(sig_lbl)

        ssid_lbl = QLabel(net["ssid"])
        ssid_lbl.setFont(QFont("Sans Serif", _fs(20),
                               QFont.Bold if net["connected"] else QFont.Normal))
        ssid_lbl.setStyleSheet(
            f"background: transparent; color: {_BLUE if net['connected'] else _DARK}; border: none;")
        rl.addWidget(ssid_lbl, stretch=1)

        if net["connected"]:
            badge = QLabel("연결됨")
            badge.setFont(QFont("Sans Serif", _fs(16), QFont.Bold))
            badge.setStyleSheet(
                f"background: #dcfce7; color: {_GREEN}; border-radius: {_fs(8)}px; padding: {_fs(4)}px {_fs(12)}px;")
            rl.addWidget(badge)

        if net["secured"]:
            lock = QLabel("🔒")
            lock.setFont(QFont("Sans Serif", _fs(16)))
            lock.setStyleSheet("background: transparent; border: none;")
            rl.addWidget(lock)

        if not net["connected"]:
            conn_btn = QPushButton("연결")
            conn_btn.setFont(QFont("Sans Serif", _fs(18), QFont.Bold))
            conn_btn.setFixedHeight(_fs(44))
            conn_btn.setFixedWidth(_fs(80))
            conn_btn.setStyleSheet(f"""
                QPushButton {{ background: {_BLUE}; color: white;
                               border-radius: {_fs(8)}px; border: none; }}
                QPushButton:pressed {{ background: #2563eb; }}
            """)
            conn_btn.clicked.connect(lambda _, n=net: self._on_connect(n))
            rl.addWidget(conn_btn)

        return row

    def _on_connect(self, net: dict):
        password = ""
        if net["secured"]:
            dlg = _WifiPasswordDialog(net["ssid"], parent=self.window())
            dlg.exec_centered(self.window().geometry())
            if dlg.result() != QDialog.Accepted:
                return
            password = dlg.get_password()

        self._list_widget.hide()
        self._set_status(f"'{net['ssid']}' 연결 중...", _BLUE)
        self._change_btn.setEnabled(False)

        self._connect_thread = _WifiConnectThread(net["ssid"], password, parent=self)
        self._connect_thread.success.connect(self._on_connected)
        self._connect_thread.failed.connect(self._on_connect_failed)
        self._connect_thread.start()

    def _on_connected(self, ssid: str):
        self._ssid_lbl.setText(ssid)
        self._ip_lbl.setText(_current_ip())
        self._set_status(f"'{ssid}' 연결 성공!", _GREEN)
        self._change_btn.setEnabled(True)
        self._change_btn.setText("네트워크 변경")
        QTimer.singleShot(3000, self._status_lbl.hide)

    def _on_connect_failed(self, msg: str):
        self._set_status(f"연결 실패: {msg}", _RED)
        self._change_btn.setEnabled(True)
        self._change_btn.setText("닫기")
        self._list_widget.show()

    def _set_status(self, text: str, color: str):
        self._status_lbl.setText(text)
        self._status_lbl.setStyleSheet(
            f"color: {color}; background: transparent; border: none;")
        self._status_lbl.show()


class _VolumeCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"QFrame {{ background-color: {_CARD}; border-radius: {_fs(16)}px; }}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(_fs(_CARD_PAD_H), _fs(_CARD_PAD_V), _fs(_CARD_PAD_H), _fs(_CARD_PAD_V))
        lay.setSpacing(_fs(14))

        top = QHBoxLayout()
        top.addWidget(_icon_label("volume.png", "♪", size=_fs(_ICON_SIZE)))
        top.addSpacing(_fs(16))

        title_lbl = QLabel("알림 음량")
        title_lbl.setFont(QFont("Sans Serif", _fs(22), QFont.Bold))
        title_lbl.setStyleSheet(f"color: {_DARK}; background: transparent; border: none;")

        self._pct_lbl = QLabel("70%")
        self._pct_lbl.setFont(QFont("Sans Serif", _fs(22), QFont.Bold))
        self._pct_lbl.setStyleSheet(f"color: {_BLUE}; background: transparent; border: none;")

        top.addWidget(title_lbl)
        top.addStretch()
        top.addWidget(self._pct_lbl)
        lay.addLayout(top)

        current_vol = self._read_volume()
        self._pct_lbl.setText(f"{current_vol}%")

        self._slider = QSlider(Qt.Horizontal)
        self._slider.setRange(0, 100)
        self._slider.setValue(current_vol)
        self._slider.setFixedHeight(_fs(40))
        self._slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 8px;
                background: #e2e8f0;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                width: {_fs(28)}px;
                height: {_fs(28)}px;
                margin: -10px 0;
                background: {_BLUE};
                border-radius: {_fs(14)}px;
            }}
            QSlider::sub-page:horizontal {{
                background: {_BLUE};
                border-radius: 4px;
            }}
        """)
        self._slider.valueChanged.connect(lambda v: self._pct_lbl.setText(f"{v}%"))
        self._slider.sliderReleased.connect(lambda: self._set_volume(self._slider.value()))
        lay.addWidget(self._slider)

        self._test_btn = QPushButton("소리 확인")
        self._test_btn.setFont(QFont("Sans Serif", _fs(20), QFont.Bold))
        self._test_btn.setFixedHeight(_fs(68))
        self._test_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #eff6ff;
                color: {_BLUE};
                border: 2px solid #bfdbfe;
                border-radius: {_fs(14)}px;
            }}
            QPushButton:pressed {{ background-color: #dbeafe; }}
            QPushButton:disabled {{
                background-color: #f1f5f9;
                color: #94a3b8;
                border-color: #e2e8f0;
            }}
        """)
        self._test_btn.clicked.connect(self._on_test_sound)
        lay.addWidget(self._test_btn)

        self._tts_btn = QPushButton("TTS 안내음 확인")
        self._tts_btn.setFont(QFont("Sans Serif", _fs(20), QFont.Bold))
        self._tts_btn.setFixedHeight(_fs(68))
        self._tts_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #f0fdf4;
                color: {_GREEN};
                border: 2px solid #bbf7d0;
                border-radius: {_fs(14)}px;
            }}
            QPushButton:pressed {{ background-color: #dcfce7; }}
            QPushButton:disabled {{
                background-color: #f1f5f9;
                color: #94a3b8;
                border-color: #e2e8f0;
            }}
        """)
        self._tts_btn.clicked.connect(self._on_test_tts)
        lay.addWidget(self._tts_btn)

    @staticmethod
    def _read_volume() -> int:
        for ctrl in ("Master", "PCM"):
            try:
                out = subprocess.check_output(
                    ["amixer", "sget", ctrl], stderr=subprocess.DEVNULL, text=True
                )
                m = re.search(r'\[(\d+)%\]', out)
                if m:
                    return int(m.group(1))
            except Exception:
                pass
        return 70

    @staticmethod
    def _set_volume(vol: int):
        for ctrl in ("Master", "PCM"):
            try:
                subprocess.call(
                    ["amixer", "sset", ctrl, f"{vol}%"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
            except Exception:
                pass

    def _on_test_sound(self):
        self._test_btn.setEnabled(False)
        self._test_btn.setText("재생 중...")
        try:
            from hardware.alarm import play_alarm
            play_alarm()
        except Exception:
            pass
        QTimer.singleShot(2000, self._stop_test_sound)

    def _stop_test_sound(self):
        try:
            from hardware.alarm import stop_alarm
            stop_alarm()
        except Exception:
            pass
        self._test_btn.setEnabled(True)
        self._test_btn.setText("소리 확인")

    def _on_test_tts(self):
        self._tts_btn.setEnabled(False)
        self._tts_btn.setText("재생 중...")
        try:
            from hardware.alarm import play_voice
            play_voice("voice.mp3")
        except Exception:
            pass
        QTimer.singleShot(5000, self._stop_test_tts)

    def _stop_test_tts(self):
        try:
            from hardware.alarm import stop_alarm
            stop_alarm()
        except Exception:
            pass
        self._tts_btn.setEnabled(True)
        self._tts_btn.setText("TTS 안내음 확인")


class _FontSizeCard(QFrame):
    _OPTIONS = [("normal", "기본"), ("large", "크게"), ("xlarge", "더크게")]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"QFrame {{ background-color: {_CARD}; border-radius: {_fs(16)}px; }}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(_fs(_CARD_PAD_H), _fs(_CARD_PAD_V), _fs(_CARD_PAD_H), _fs(_CARD_PAD_V))
        lay.setSpacing(_fs(14))

        top = QHBoxLayout()
        top.addWidget(_icon_label("font.png", "Aa", size=_fs(_ICON_SIZE)))
        top.addSpacing(_fs(16))

        title_lbl = QLabel("글자 크기")
        title_lbl.setFont(QFont("Sans Serif", _fs(22), QFont.Bold))
        title_lbl.setStyleSheet(f"color: {_DARK}; background: transparent; border: none;")
        top.addWidget(title_lbl)
        top.addStretch()
        lay.addLayout(top)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(_fs(12))

        self._btns: dict = {}
        for key, label in self._OPTIONS:
            btn = QPushButton(label)
            btn.setFont(QFont("Sans Serif", _fs(20), QFont.Bold))
            btn.setFixedHeight(_fs(64))
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            btn.clicked.connect(lambda _, k=key: self._on_select(k))
            self._btns[key] = btn
            btn_row.addWidget(btn)
        lay.addLayout(btn_row)

        self._notice_lbl = QLabel("")
        self._notice_lbl.setFont(QFont("Sans Serif", _fs(18)))
        self._notice_lbl.setAlignment(Qt.AlignCenter)
        self._notice_lbl.setStyleSheet(f"color: {_GRAY}; background: transparent; border: none;")
        lay.addWidget(self._notice_lbl)

        self._refresh_styles()

    def _refresh_styles(self):
        from utils.ui_prefs import get_font_size_key
        current = get_font_size_key()
        for key, btn in self._btns.items():
            if key == current:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {_BLUE};
                        color: white;
                        border-radius: {_fs(12)}px;
                        border: none;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: #f1f5f9;
                        color: {_DARK};
                        border-radius: {_fs(12)}px;
                        border: 2px solid #e2e8f0;
                    }}
                    QPushButton:pressed {{ background-color: #e2e8f0; }}
                """)

    def _on_select(self, key: str):
        from utils.ui_prefs import get_font_size_key, set_font_size
        if key == get_font_size_key():
            return
        set_font_size(key)
        self._refresh_styles()
        self._notice_lbl.setText("재시작 후 적용됩니다  •  아래 '재시작' 버튼을 눌러주세요")


class _ControlCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"QFrame {{ background-color: {_CARD}; border-radius: {_fs(16)}px; }}")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(_fs(_CARD_PAD_H), _fs(_CARD_PAD_V), _fs(_CARD_PAD_H), _fs(_CARD_PAD_V))
        lay.setSpacing(_fs(14))

        top = QHBoxLayout()
        top.addWidget(_icon_label("control.png", "⚙", size=_fs(_ICON_SIZE)))
        top.addSpacing(_fs(16))

        title_lbl = QLabel("기기 제어")
        title_lbl.setFont(QFont("Sans Serif", _fs(22), QFont.Bold))
        title_lbl.setStyleSheet(f"color: {_DARK}; background: transparent; border: none;")
        top.addWidget(title_lbl)
        top.addStretch()
        lay.addLayout(top)

        restart_btn = QPushButton("재시작")
        restart_btn.setMinimumHeight(_fs(80))
        restart_btn.setFont(QFont("Sans Serif", _fs(24), QFont.Bold))
        restart_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #fff3e0;
                color: {_ORANGE};
                border: 2px solid #fed7aa;
                border-radius: {_fs(16)}px;
            }}
            QPushButton:pressed {{ background-color: #ffe0b2; }}
        """)
        restart_btn.clicked.connect(self._restart)
        lay.addWidget(restart_btn)

        exit_btn = QPushButton("앱 종료")
        exit_btn.setMinimumHeight(_fs(80))
        exit_btn.setFont(QFont("Sans Serif", _fs(24), QFont.Bold))
        exit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #fee2e2;
                color: #dc2626;
                border: 2px solid #fca5a5;
                border-radius: {_fs(16)}px;
            }}
            QPushButton:pressed {{ background-color: #fecaca; }}
        """)
        exit_btn.clicked.connect(self._exit)
        lay.addWidget(exit_btn)

    @staticmethod
    def _restart():
        ret = os.system("pm2 restart carefull")
        if ret != 0:
            # pm2 없는 환경(직접 실행): 현재 프로세스를 동일 인자로 교체
            os.execv(sys.executable, [sys.executable] + sys.argv)

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

        # 1. 얼굴 임베딩 삭제 (서버)
        try:
            from api.client import delete_face_embedding
            server_ok = delete_face_embedding()
        except Exception as e:
            print(f"[FACE DELETE] server: {e}")

        # 2. 얼굴 임베딩 삭제 (로컬)
        try:
            with open(_DB_PATH, "w", encoding="utf-8") as f:
                json.dump({}, f)
        except Exception as e:
            print(f"[FACE DELETE] local: {e}")

        # 3. 임베딩 캐시 무효화
        try:
            from auth.authenticate import invalidate_embedding_cache
            invalidate_embedding_cache()
        except Exception:
            pass

        # 4. 지문 전체 삭제 (하드웨어 센서 + 서버 DB)
        try:
            from api.client import fetch_fingerprints, delete_fingerprint
            from hardware.fingerprint import get_fingerprint_manager
            fps = fetch_fingerprints()
            fm = get_fingerprint_manager()
            for fp in fps:
                slot_id = fp["slot_id"]
                try:
                    fm.delete_template(slot_id)
                except Exception as e:
                    print(f"[FP DELETE HW] slot {slot_id}: {e}")
                try:
                    delete_fingerprint(slot_id)
                except Exception as e:
                    print(f"[FP DELETE SERVER] slot {slot_id}: {e}")
        except Exception as e:
            print(f"[FP DELETE] {e}")

        self.done.emit(server_ok)


class _FaceCard(QFrame):
    all_deleted = pyqtSignal()  # 얼굴+지문 삭제 완료 시 발생

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self.setStyleSheet(f"QFrame {{ background-color: {_CARD}; border-radius: {_fs(16)}px; }}")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(_fs(_CARD_PAD_H), _fs(_CARD_PAD_V), _fs(_CARD_PAD_H), _fs(_CARD_PAD_V))
        outer.setSpacing(_fs(12))

        header = QHBoxLayout()
        header.addWidget(_icon_label("face.png", "👤", size=_fs(_ICON_SIZE)))
        header.addSpacing(_fs(12))

        title = QLabel("사용자 얼굴")
        title.setFont(QFont("Sans Serif", _fs(22), QFont.Bold))
        title.setStyleSheet(f"color: {_DARK}; background: transparent; border: none;")
        header.addWidget(title)
        header.addStretch()

        self._badge = QLabel()
        self._badge.setFont(QFont("Sans Serif", _fs(18), QFont.Bold))
        header.addWidget(self._badge)
        outer.addLayout(header)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #e2e8f0;")
        outer.addWidget(sep)

        self._del_btn = QPushButton("등록된 사용자 삭제")
        self._del_btn.setMinimumHeight(_fs(80))
        self._del_btn.setFont(QFont("Sans Serif", _fs(22), QFont.Bold))
        self._del_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #fee2e2;
                color: {_RED};
                border: 2px solid #fca5a5;
                border-radius: {_fs(16)}px;
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
                f"background: #dcfce7; color: {_GREEN}; border-radius: {_fs(10)}px; padding: {_fs(6)}px {_fs(18)}px;"
            )
        else:
            self._badge.setText("미등록")
            self._badge.setStyleSheet(
                f"background: #e2e8f0; color: #64748b; border-radius: {_fs(10)}px; padding: {_fs(6)}px {_fs(18)}px;"
            )
        self._del_btn.setEnabled(has)

    def _on_delete_clicked(self):
        box = QMessageBox(self)
        box.setWindowTitle("사용자 삭제")
        box.setText("등록된 얼굴·지문 정보를\n모두 삭제하시겠습니까?")
        box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        box.setDefaultButton(QMessageBox.No)
        box.button(QMessageBox.Yes).setText("삭제")
        box.button(QMessageBox.No).setText("취소")
        box.setStyleSheet(f"""
            QMessageBox {{ background: white; }}
            QLabel {{ font-size: {_fs(22)}px; color: #1e293b; }}
            QPushButton {{ min-height: {_fs(60)}px; min-width: {_fs(110)}px; font-size: {_fs(20)}px; border-radius: {_fs(10)}px; }}
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
        self.all_deleted.emit()


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
        self.setStyleSheet(f"QFrame {{ background-color: {_CARD}; border-radius: {_fs(16)}px; }}")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(_fs(_CARD_PAD_H), _fs(_CARD_PAD_V), _fs(_CARD_PAD_H), _fs(_CARD_PAD_V))
        outer.setSpacing(_fs(12))

        # 헤더 행
        header = QHBoxLayout()
        header.addWidget(_icon_label("fingerprint.png", "🔒", size=_fs(_ICON_SIZE)))
        header.addSpacing(_fs(12))

        title = QLabel("지문 관리")
        title.setFont(QFont("Sans Serif", _fs(22), QFont.Bold))
        title.setStyleSheet(f"color: {_DARK}; background: transparent; border: none;")
        header.addWidget(title)
        header.addStretch()

        add_btn = QPushButton("추가 등록")
        add_btn.setFont(QFont("Sans Serif", _fs(18), QFont.Bold))
        add_btn.setFixedHeight(_fs(48))
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {_BLUE};
                color: white;
                border-radius: {_fs(10)}px;
                padding: 0 {_fs(18)}px;
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
        self._list_lay.setSpacing(_fs(8))
        outer.addWidget(self._list_container)

        self._status_lbl = QLabel("불러오는 중...")
        self._status_lbl.setFont(QFont("Sans Serif", _fs(18)))
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
        lay.setContentsMargins(0, _fs(4), 0, _fs(4))
        lay.setSpacing(_fs(12))

        badge = QLabel(str(fp["slot_id"]))
        badge.setFont(QFont("Sans Serif", _fs(18), QFont.Bold))
        badge.setFixedSize(_fs(40), _fs(40))
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(f"background: {_BLUE}; color: white; border-radius: {_fs(20)}px;")
        lay.addWidget(badge)

        name_lbl = QLabel(fp.get("label", "지문"))
        name_lbl.setFont(QFont("Sans Serif", _fs(20)))
        name_lbl.setStyleSheet(f"color: {_DARK}; background: transparent; border: none;")
        lay.addWidget(name_lbl)

        if fp.get("registered_at"):
            date_lbl = QLabel(str(fp["registered_at"])[:10])
            date_lbl.setFont(QFont("Sans Serif", _fs(18)))
            date_lbl.setStyleSheet(f"color: {_GRAY}; background: transparent; border: none;")
            lay.addWidget(date_lbl)

        lay.addStretch()

        del_btn = QPushButton("삭제")
        del_btn.setFont(QFont("Sans Serif", _fs(18)))
        del_btn.setFixedHeight(_fs(48))
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: #fee2e2;
                color: {_RED};
                border: 1.5px solid #fca5a5;
                border-radius: {_fs(8)}px;
                padding: 0 {_fs(14)}px;
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
        root.setContentsMargins(_fs(80), _fs(24), _fs(80), _fs(24))
        root.setSpacing(0)

        # 상단 헤더
        header = QHBoxLayout()
        back_btn = QPushButton("← 메인으로")
        back_btn.setFont(QFont("Sans Serif", _fs(22)))
        back_btn.setFixedHeight(_fs(64))
        back_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background: white;
                color: #374151;
                border: 2px solid #d0d5dd;
                border-radius: {_fs(14)}px;
                padding: 4px {_fs(24)}px;
            }}
            QPushButton:pressed {{ background: #f0f0f0; }}
        """)
        back_btn.clicked.connect(lambda: self._app.show_screen("home"))

        title = QLabel("설정")
        title.setFont(QFont("Sans Serif", _fs(28), QFont.Bold))
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

        root.addSpacing(_fs(14))

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
        c_lay.setSpacing(_fs(14))
        c_lay.setContentsMargins(0, 0, 0, 0)

        c_lay.addWidget(_WifiCard())
        c_lay.addWidget(_StatusCard("server.png", "서버", "서버 통신", "통신 가능", True))
        c_lay.addWidget(_VolumeCard())
        c_lay.addWidget(_FontSizeCard())

        self._face_card = _FaceCard()
        c_lay.addWidget(self._face_card)

        self._fp_card = _FingerprintCard(self._app)
        c_lay.addWidget(self._fp_card)

        self._face_card.all_deleted.connect(self._fp_card.refresh)

        c_lay.addWidget(_ControlCard())
        c_lay.addStretch()

        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

        root.addSpacing(_fs(8))

        ver = QLabel("Smart Medication Dispenser v1.0")
        ver.setFont(QFont("Sans Serif", _fs(16)))
        ver.setAlignment(Qt.AlignCenter)
        ver.setStyleSheet(f"color: {_GRAY};")
        root.addWidget(ver)
