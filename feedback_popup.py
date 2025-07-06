# feedback_popup.py

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt
from send_feedback import send_feedback_email
import shared

class FeedbackPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Share your experience")
        self.setFixedSize(360, 140)

        layout = QVBoxLayout()

        label = QLabel("Would you like to share your experience with Impulse?")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        btn_layout = QHBoxLayout()
        btn_good = QPushButton("👍 Good")
        btn_bad = QPushButton("👎 Bad")
        btn_ignore = QPushButton("❌ Ignore")

        btn_good.clicked.connect(lambda: self.handle_feedback("Good"))
        btn_bad.clicked.connect(lambda: self.handle_feedback("Bad"))
        btn_ignore.clicked.connect(self.reject)

        for btn in (btn_good, btn_bad, btn_ignore):
            btn_layout.addWidget(btn)

        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def handle_feedback(self, sentiment):
        send_feedback_email(sentiment)
        self.accept()
