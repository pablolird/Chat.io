from datetime import datetime
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QScrollArea,
    QSizePolicy
)
from PySide6.QtCore import (
    QSize,
    Qt,
    QTimer
)
import os

class chatInput(QWidget):
    def __init__(self):
        super().__init__()

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #393E46;")

        self.m_layout = QHBoxLayout()
        self.m_layout.setContentsMargins(10,10,10,10)
        self.setLayout(self.m_layout)

        self.m_inputBar = QLineEdit()
        
        self.m_inputBar.setPlaceholderText("Write a message...")
        
        self.m_inputBar.setStyleSheet("""QLineEdit { 
                                            padding: 15px; 
                                            background-color: #222831;
                                            border-radius: 10px;
                                            outline: none;
                                            color: white;
                                        }

                                        QLineEdit:focus {
                                            border: 1px solid gray;
                                            outline: none;
                                        }""")

        self.m_challengeButton = QPushButton()
        self.m_challengeButton.setIconSize(QSize(32,32))

        self.m_layout.addWidget(self.m_inputBar,8)
        self.m_layout.addWidget(self.m_challengeButton,1)


class Message(QWidget):
    def __init__(self, username, text: str, timestamp: str, is_admin, is_sender: bool = False):
        super().__init__()

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.timestamp = QLabel(timestamp)
        self.timestamp.setStyleSheet("background-color: transparent; font-size: 12px; color: #fff")

        self.bubble = QWidget()
        self.bubbleLayout = QVBoxLayout()
        self.bubble.setLayout(self.bubbleLayout)        

        self.text = QLabel(text)
        self.text.setStyleSheet("padding: 0px;")
        self.text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.text.setCursor(Qt.CursorShape.IBeamCursor)

        self.m_acceptButton = QPushButton("Accept Challenge")
        self.m_acceptButton.setStyleSheet("""
                                QPushButton {
                                border: 1px solid #6b5400; background-color: #ffc800;
                                }

                            QPushButton:focus {
                                border: 1px solid grey;
                                outline: none;
                            }

                            QPushButton:hover {
                                background-color: #d9b11e;
                            }""")

        # Optional: Align left/right depending on sender
        if is_sender:
            self.bubbleLayout.addWidget(self.text)
            layout.addStretch()
            layout.addWidget(self.bubble)
            layout.addWidget(self.timestamp)
            self.bubble.setStyleSheet("background-color: green; border-radius: 10px; padding: 10px; color: white;")
        elif username=="SYSTEM":
            self.bubbleLayout.addWidget(self.text)
            self.text.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.bubble)
            self.bubble.setStyleSheet("background-color: #c7c3b9; border-radius: 10px; padding: 10px; color: #242321;")
        elif username=="CHALLENGE_NOTICE":
            self.bubbleLayout.addWidget(self.text)
            print("HOLA")
            if is_admin:
                print("HOLA SOY ADMIN")
                self.bubbleLayout.addWidget(self.m_acceptButton)
            self.text.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.bubble)
            self.bubble.setStyleSheet("background-color: yellow; border-radius: 10px; padding: 10px; color: #242321;")
        else:
            self.username = QLabel(username)
            self.username.setStyleSheet("padding: 0px; color: grey; font-size: 12px;")
            self.bubbleLayout.addWidget(self.username)
            self.bubbleLayout.addWidget(self.text)
            layout.addWidget(self.timestamp)
            layout.addWidget(self.bubble)
            layout.addStretch()
            self.bubble.setStyleSheet("background-color: #3d3d29; border-radius: 10px; padding: 10px; color: white;")

        self.setLayout(layout)
        self.text.setWordWrap(True)
        self.text.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.text.setMaximumWidth(400)  # You can adjust or use a percentage


class ChatArea(QWidget):
    def __init__(self):
        super().__init__()

        self.m_scroll = QScrollArea()
        self.m_scroll.setWidgetResizable(True)

        self.m_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.m_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.m_container = QWidget()
        self.m_container_layout = QVBoxLayout()
        self.m_container_layout.setAlignment(Qt.AlignTop)
        self.m_container.setLayout(self.m_container_layout)

        #self.m_container.setStyleSheet("background-color: #222831; border-radius: 10px")
        self.setStyleSheet("background-color: #222831; border-radius: 10px")

        self.m_container.setObjectName("ChatAreaContainer")
                
        self.m_container.setStyleSheet(""" QWidget#ChatAreaContainer {
                            background: qlineargradient(
                                spread:pad,
                                x1:0, y1:0, x2:0, y2:1,
                                stop:0 #222831  ,
                                stop:1 #1d222a
                            );
                            border-radius: 10px;
                        }""")
        

        self.m_scroll.setWidget(self.m_container)

        m_layout = QVBoxLayout(self)
        m_layout.addWidget(self.m_scroll)

        self.setLayout(m_layout)

    def add_message(self,username, text, timestamp, is_admin, is_sender):
        now = datetime.now()
        current_time = timestamp

        message = Message(username,text, current_time, is_admin, is_sender)
        # Set message max width relative to ChatArea
        max_width = int(self.width() * 0.6)
        message.bubble.setMaximumWidth(max_width)
        self.m_container_layout.addWidget(message)

        # Scroll reliably using a delayed scroll on the vertical scrollbar
        def scroll_later():
            bar = self.m_scroll.verticalScrollBar()
            if bar.value() >= bar.maximum() - 300:  # Only scroll if already near bottom
                bar.setValue(bar.maximum())

        # Delay twice to make sure layout and repaint are finished
        QTimer.singleShot(0, lambda: QTimer.singleShot(0, scroll_later))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Update max width of all bubbles on resize
        for i in range(self.m_container_layout.count()):
            widget = self.m_container_layout.itemAt(i).widget()
            if isinstance(widget, Message):
                widget.bubble.setMaximumWidth(int(self.width() * 0.6))
