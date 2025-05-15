from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QStackedWidget
)
from PySide6.QtCore import (
    Qt,
    Signal
)
from ui.startpage.start_classes import inputField
from ui.mainpage.group_info import GroupInfo
from ui.mainpage.chat_area import ChatArea, chatInput
import os

class ChatView(QWidget): # Definition of a chat space class
    def __init__(self, groupname):
        super().__init__()

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #393E46;")

        self.m_layout = QVBoxLayout() # m_layout definition
        self.m_layout.setAlignment(Qt.AlignTop)
        self.m_layout.setSpacing(0)
        self.m_layout.setContentsMargins(0,0,0,0)

        self.m_groupInfo = GroupInfo(groupname)
        self.m_chatArea = ChatArea()
        self.m_inputMessageBar = chatInput() # Bar to write messages

        self.m_layout.addWidget(self.m_groupInfo, 3)
        self.m_layout.addWidget(self.m_chatArea, 20)
        self.m_layout.addWidget(self.m_inputMessageBar, 2)

        self.setLayout(self.m_layout)


class initialChat(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("InitialChat")  # Name the widget

        self.setAttribute(Qt.WA_StyledBackground, True)
        
        self.setStyleSheet(""" QWidget#InitialChat {
                            background: qlineargradient(
                                spread:pad,
                                x1:0, y1:0, x2:0, y2:1,
                                stop:0 #222831  ,
                                stop:1 #393E46
                            );
                            border-radius: 10px;
                            padding: 10px;
                            color: white; border-radius: 0;
                        }""")
        
        self.m_title = QLabel()
        self.m_title.setPixmap(QPixmap(os.path.join("assets","icons","logo.png")).scaled(300,300, Qt.KeepAspectRatio))
        self.m_title.setStyleSheet("font-size: 36px; color: white; font-weight: bold;")

        self.m_subtitle = QLabel("#WeChat #SkibidiGroup")
        self.m_subtitle.setStyleSheet("font-size: 18px; color: grey;")

        self.m_title.setAlignment(Qt.AlignCenter)
        self.m_subtitle.setAlignment(Qt.AlignCenter)

        self.m_layout = QVBoxLayout()
        self.m_layout.setAlignment(Qt.AlignCenter)

        self.m_layout.addWidget(self.m_title)
        self.m_layout.addWidget(self.m_subtitle)
        
        self.setLayout(self.m_layout)


class groupForm(QWidget):
    warn = Signal(str, bool)

    def __init__(self, name, placeholder):
        super().__init__()
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName(name)
        self.setStyleSheet(f"QWidget#{name}"+"""{
                            background: qlineargradient(
                                spread:pad,
                                x1:0, y1:0, x2:0, y2:1,
                                stop:0 #222831  ,
                                stop:1 #393E46
                            );
                            border-radius: 10px;
                            padding: 10px;
                            color: white; border-radius: 0;
                           }
                            QPushButton { background-color: #948979; padding: 10px; color: #222831 }
                        """)


        self.m_groupName = inputField(placeholder)
        self.m_send = QPushButton("Submit")
        self.m_send.setFixedWidth(100)
        self.m_warning = QLabel()
        self.m_warning.setAlignment(Qt.AlignCenter)

        self.m_layout = QVBoxLayout()
        self.m_layout.addStretch()
        self.m_layout.addWidget(self.m_groupName)
        self.m_layout.addWidget(self.m_send)
        self.m_layout.addStretch()
        self.m_layout.addWidget(self.m_warning)
        #self.m_layout.setAlignment(Qt.AlignCenter)

        self.setLayout(self.m_layout)

        self.warn.connect(self.setWarning)

    
    def setWarning(self, text, flag):
        self.m_warning.setText(text)
        if flag:
            self.m_warning.setStyleSheet("color: #40e215;")
        else:
            self.m_warning.setStyleSheet("color: #ff5454;")

class ChatsContainer(QWidget):
    def __init__(self):
        super().__init__()

        self.m_chats = {}
        self.m_stack = QStackedWidget()

        self.m_createGroup = groupForm("createGroup", "Enter group name...")
        self.m_joinGroup = groupForm("joinGroup", "Enter group ID...")

        self.m_stack.insertWidget(0,initialChat())
        self.m_stack.insertWidget(1,self.m_createGroup)
        self.m_stack.insertWidget(2,self.m_joinGroup)

        self.m_layout = QVBoxLayout()

        self.m_layout.addWidget(self.m_stack)
        self.setLayout(self.m_layout)
        self.m_layout.setSpacing(0)
        self.m_layout.setContentsMargins(0,0,0,0)
