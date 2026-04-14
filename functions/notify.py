import sys
import os
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QFrame
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtGui import QCursor

def system_notification(title, description):
    os.system(f'notify-send "{title}" "{description}" -a "OpenHomeHUB"')
def test_mode_enable():    
    return os.path.isfile("test.txt")
def music_advice(text):
    
    if os.path.isfile("custom/musical_notify.mp3"):
        mp3_path = "custom/musical_notify.mp3"
    else:
        mp3_path = "custom/musical_notify_basic.mp3"
    
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)

    class Alert(QWidget):
        def __init__(self):
            super().__init__()

            self.setWindowFlags(
                Qt.WindowType.FramelessWindowHint | 
                Qt.WindowType.WindowStaysOnTopHint
            )
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

            layout_esterno = QVBoxLayout(self)
            layout_esterno.setAlignment(Qt.AlignmentFlag.AlignCenter)

            main_frame = QFrame()
            main_frame.setFixedSize(600, 300) 
            main_frame.setStyleSheet("""
                QFrame {
                    background-color: #1e1e1e;
                    border: 2px solid #e53935;
                    border-radius: 20px;
                }
                QLabel {
                    color: white;
                    font-size: 24px;
                    font-weight: bold;
                    background: transparent;
                    border: none;
                }
                QPushButton {
                    background-color: #e53935;
                    color: white;
                    border-radius: 10px;
                    padding: 15px;
                    font-size: 18px;
                    font-weight: bold;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #ff5252;
                }
            """)

            layout_principale = QVBoxLayout(main_frame)
            layout_principale.setContentsMargins(40, 40, 40, 40)
            layout_esterno.addWidget(main_frame)

            label = QLabel(text)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setWordWrap(True)
            layout_principale.addWidget(label)

            btn = QPushButton("CHIUDI ALLARME")
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(self.close_all)
            layout_principale.addWidget(btn)

            self.audio_output = QAudioOutput()
            self.player = QMediaPlayer()
            self.player.setAudioOutput(self.audio_output)
            self.player.setSource(QUrl.fromLocalFile(mp3_path))
            self.audio_output.setVolume(0.8)

            self.player.mediaStatusChanged.connect(self.loop_audio)
            self.player.play()

            self.focus_timer = QTimer()
            self.focus_timer.timeout.connect(self.bring_front)
            self.focus_timer.start(2000)

            if not test_mode_enable():
                self.showFullScreen()
            else:
                self.show()

        def loop_audio(self, status):
            if status == QMediaPlayer.MediaStatus.EndOfMedia:
                self.player.setPosition(0)
                self.player.play()

        def bring_front(self):
            self.raise_()
            self.activateWindow()

        def close_all(self):
            self.player.stop()
            self.close()
            QApplication.quit()

    w = Alert()
    sys.exit(app.exec())