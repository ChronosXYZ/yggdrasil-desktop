import os
from pathlib import Path
from re import S
from xdg import xdg_config_home
import subprocess
import sys
from threading import Thread
from PySide6.QtGui import QIcon, QCursor
from PySide6.QtWidgets import QApplication, QWidget, QSystemTrayIcon, QMenu
from PySide6.QtCore import Signal

YGGDRASIL_BIN = Path("/usr/bin/yggdrasil") # FIXME

CONFIG_DIR_PATH = xdg_config_home() / "yggdrasil"

CONFIG_FILE_PATH = CONFIG_DIR_PATH / "yggdrasil.conf"
YGGDRASIL_DAEMON_LOG_FILE_PATH = CONFIG_DIR_PATH / "yggdrasil.log"

class YggdrasilRunner(Thread):
    def __init__(self, sig: Signal):
        Thread.__init__(self, daemon=True)

        self.sig = sig

    def run(self):
        logFile = open(str(YGGDRASIL_DAEMON_LOG_FILE_PATH), "w")
        self.proc = subprocess.Popen(["pkexec", YGGDRASIL_BIN, "-useconffile", str(CONFIG_FILE_PATH)], stdout=logFile)
        self.proc.wait()
        self.sig.emit(True)
        self.proc = None
        logFile.close()
    
    def stop(self):
        if hasattr(self, 'proc'): subprocess.run(["pkexec", "kill", "-TERM", str(self.proc.pid)])

class YggSystemTrayIcon(QSystemTrayIcon):
    yggSignal = Signal(bool)

    def __init__(self, icon, parent=None):
        QSystemTrayIcon.__init__(self, icon, parent)

        menu = QMenu(parent)

        self._startYggEntry = menu.addAction("Start Yggdrasil")
        self._startYggEntry.triggered.connect(self._startYgg)

        self._stopYggEntry = menu.addAction("Stop Yggdrasil")
        self._stopYggEntry.triggered.connect(self._stopYgg)
        self._stopYggEntry.setDisabled(True)

        menu.addSeparator()

        openConfigEntry = menu.addAction("Open config")
        openConfigEntry.triggered.connect(self._openConfigFile)

        menu.addSeparator()

        exitEntry = menu.addAction("Exit")
        exitEntry.triggered.connect(self._exitApp)

        self.setContextMenu(menu)
        self.activated.connect(self._onTrayIconActivated)

        self.yggSignal.connect(self._onYggDied)
        self.isRunning = False

    def _onTrayIconActivated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.contextMenu().popup(QCursor.pos())

    def _startYgg(self):
        print("start ygg")
        self.runner = YggdrasilRunner(self.yggSignal)
        self.isRunning = True
        self._startYggEntry.setDisabled(True)
        self._stopYggEntry.setEnabled(True)
        self.runner.start()

    def _stopYgg(self):
        self.runner.stop()
    
    def _exitApp(self):
        sys.exit(0)

    def _onYggDied(self):
        self.isRunning = False
        self._stopYggEntry.setDisabled(True)
        self._startYggEntry.setEnabled(True)

    def _openConfigFile(self):
        subprocess.run(["xdg-open", str(CONFIG_FILE_PATH)])


if __name__ == "__main__":
    # generate config
    if not CONFIG_DIR_PATH.exists():
        os.makedirs(str(CONFIG_DIR_PATH))
    if not CONFIG_FILE_PATH.exists():
        conf = subprocess.check_output([YGGDRASIL_BIN, "-genconf"])
        confFile = open(str(CONFIG_FILE_PATH), "w")
        confFile.write(conf.decode("utf-8"))
        confFile.close()

    app = QApplication(sys.argv)
    w = QWidget()
    tray = YggSystemTrayIcon(QIcon("tray.png"), w)
    tray.show()

    sys.exit(app.exec())
