from PySide6.QtCore import (
    Qt, 
    Signal, 
    Signal)

from PySide6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QScrollArea,
)
from PySide6.QtGui import (
    QIcon,
    QPixmap,
)

class GroupTitle(QWidget):
    def __init__(self, name):
        super().__init__()

        self.m_layout = QHBoxLayout()

        self.m_title = QLabel(name)
        self.m_icon = QLabel()
        self.m_icon.setPixmap(QPixmap("assets/icons/Multiple-User--Streamline-Pixel.svg"))

        self.m_layout.addWidget(self.m_icon)
        self.m_layout.addWidget(self.m_title)
        
        self.setLayout(self.m_layout)
        self.m_layout.addStretch()
        self.m_layout.setContentsMargins(15,8,15,8)
        self.m_layout.setSpacing(0)


class GroupConnected(QWidget):
    def __init__(self, count):
        super().__init__()

        self.m_layout = QHBoxLayout()

        self.m_title = QLabel(f"{count} users online")
        self.m_icon = QLabel()

        icon = QIcon("assets/icons/Interface-Essential-Information-Circle-2--Streamline-Pixel.svg")

        self.m_icon.setPixmap(icon.pixmap(16,16))
        

        self.m_layout.addWidget(self.m_icon)
        self.m_layout.addWidget(self.m_title)
        
        self.setLayout(self.m_layout)
        self.m_layout.addStretch()
        self.m_layout.setContentsMargins(15,8,15,8)
        self.m_layout.setSpacing(0)

    def updateCount(self, count):
        self.m_title.setText(f"{count} users online")


class Group(QWidget):
    clicked = Signal()  # Custom signal for click

    def __init__(self, name, chatID):
        super().__init__()

        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setStyleSheet("""
            Group {
                background-color: #222831;
                padding: 10px;
                border-radius: 10px;
                border: 1px solid #1f252d;
            }
            
            QWidget::hover {
                background-color:  #1f252d;
            }

            QWidget[selected="true"] {
                background-color:  #15191e;  /* Selected color */
            }""")

        self.m_chatID = chatID

        self.m_groupTitle = GroupTitle(name)
        self.m_groupInfo = GroupConnected(0)

        self.m_groupTitle.setStyleSheet("font-size: 20px; color: white; background-color: transparent; padding: 2px;")
        self.m_groupInfo.setStyleSheet("font-size: 16px; color: #393E46; background-color: transparent; padding: 2px;")

        self.m_layout = QVBoxLayout()

        self.m_layout.addWidget(self.m_groupTitle)
        self.m_layout.addWidget(self.m_groupInfo)
        self.setLayout(self.m_layout)

        self.m_layout.setSpacing(0)
        self.m_layout.setContentsMargins(0,0,0,0)


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
    
    def setSelected(self, is_selected):
        self.setProperty("selected", is_selected)
        self.style().unpolish(self)
        self.style().polish(self)


class GroupBar(QWidget): # Definition of group bar class
    def __init__(self):
        super().__init__()

        self.m_groups = []

        self.m_scroll = QScrollArea()
        self.m_scroll.setWidgetResizable(True)
        self.m_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.m_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.m_container = QWidget()
        self.m_container.setStyleSheet("background-color: transparent; border: none;")
        self.m_container_layout = QVBoxLayout()
        self.m_container_layout.setAlignment(Qt.AlignTop)
        self.m_container.setLayout(self.m_container_layout)

        self.m_scroll.setWidget(self.m_container)

        self.m_layout = QVBoxLayout(self)
        self.m_layout.addWidget(self.m_scroll)

        self.setLayout(self.m_layout)

        self.m_container_layout.setContentsMargins(3,3,3,3)
        self.m_layout.setContentsMargins(0,0,0,0)
        
        #self.m_scroll.setAttribute(Qt.WA_StyledBackground, True)
        self.m_scroll.setStyleSheet("padding: 15px;")

        self.m_scroll.setObjectName("GroupScrollArea")  # Set object name before styling

        self.setStyleSheet("""
            QWidget#GroupScrollArea {
                background: qlineargradient(
                    spread:pad,
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 #222831,
                    stop:1 #393E46
                );
                padding: 15px;
                color: white;
                border: none;
                border-right: 1px solid #1f252d;
            }
        """)

