import os
from PySide6.QtCore import (
    QSize, 
    Qt,
    Signal
)
from PySide6.QtWidgets import (
    QPushButton,
    QVBoxLayout,
    QGridLayout,
    QWidget,
    QStackedWidget,
    QLabel
)
from PySide6.QtGui import QIcon
from ui.mainpage.chat_view import ChatView
from ui.startpage.start_classes import inputField
from ui.mainpage.group_info import GroupDescription, MemberInfo
import os

class addGroupsBarButton(QPushButton):
    def __init__(self, path, text):
        super().__init__()   

        self.setStyleSheet("""                           
                            QPushButton:focus {
                                outline: none;
                            }
                            QPushButton {
                                border: 1px solid #1f252d;
                                background-color: #222831;
                                outline: none;
                                font-size: 20px;
                                color: white;
                                padding: 10px;
                                border-radius: 10px;
                            }
                                       
                            QPushButton::hover {
                                background-color:  #1f252d;
                            }

                            QPushButton[selected="true"] {
                                background-color:  #15191e;  /* Selected color */
                            }""")

        self.setText(text)
        self.setIcon(QIcon(path))
        self.setCursor(Qt.PointingHandCursor)
        self.setIconSize(QSize(24,24))
        self.setLayoutDirection(Qt.LeftToRight)
    
    def setSelected(self, is_selected):
        self.setProperty("selected", is_selected)
        self.style().unpolish(self)
        self.style().polish(self)

class groupForm(QWidget):
    warn = Signal(str, bool)

    def __init__(self, name, placeholder):
        super().__init__()
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName(name)
        self.setStyleSheet(f"QWidget#{name}"+"""{
                            border-radius: 10px;
                            border: none;
                            color: white; border-radius: 0;
                           }
                            QPushButton { background-color: #948979; padding: 10px; }
                        """)


        self.m_groupName = inputField(placeholder)
        self.m_send = QPushButton("Submit")
        self.m_warning = QLabel()
        self.m_warning.setAlignment(Qt.AlignCenter)
        self.m_warning.setWordWrap(True)
        self.m_warning.setStyleSheet("background-color: transparent; border: none;")

        self.m_layout = QVBoxLayout()
        self.m_layout.addWidget(self.m_groupName)
        self.m_layout.addWidget(self.m_send)
        self.m_layout.addWidget(self.m_warning)

        self.setLayout(self.m_layout)

        self.warn.connect(self.setWarning)

    
    def setWarning(self, text, flag):
        self.m_warning.setText(text)
        if flag:
            self.m_warning.setStyleSheet("color: #40e215; border: none;")
        else:
            self.m_warning.setStyleSheet("color: #ff5454; border: none;")

class addGroupsBar(QWidget):
    def __init__(self):
        super().__init__()

        self.setObjectName("addGroupsBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
                                background: qlineargradient(
                                spread:pad,
                                x1:0, y1:0, x2:0, y2:1, stop:0 #222831, stop:1 #393E46);
                                border-radius: 10px;
                                padding: 15px;
                                color: white; border-radius: 0;
                           """)
    
        self.m_layout = QVBoxLayout()

        self.m_joinGroup = addGroupsBarButton(os.path.join("assets","icons","Search-User--Streamline-Pixel.svg"), "Join existing group")
        self.m_createGroup = addGroupsBarButton(os.path.join("assets","icons","User-Single-Aim--Streamline-Pixel.svg"), "Create group")

        self.m_buttonsContainer = QWidget()
        self.m_buttonsContainer.setStyleSheet("background-color: transparent;")
        self.m_buttonsLayout = QVBoxLayout()
        self.m_buttonsContainer.setLayout(self.m_buttonsLayout)
        self.m_buttonsLayout.addWidget(self.m_joinGroup)
        self.m_buttonsLayout.addWidget(self.m_createGroup)
        
        self.m_stack = QStackedWidget()
        self.m_stack.setStyleSheet("background-color: transparent; border: none; border-top: 1px solid #1f252d")
        self.m_createGroupForm = groupForm("createGroup", "Enter group name...")
        self.m_joinGroupForm = groupForm("joinGroup", "Enter group ID...")
        self.m_joinGroup.setSelected(True)

        self.m_stack.addWidget(self.m_joinGroupForm)
        self.m_stack.addWidget(self.m_createGroupForm)


        self.m_layout.addWidget(self.m_buttonsContainer)
        self.m_layout.addWidget(self.m_stack)

        self.setLayout(self.m_layout)
        self.m_layout.addStretch()
        self.m_layout.setContentsMargins(0,0,0,0)
        self.m_layout.setSpacing(0)

        self.m_joinGroup.clicked.connect(lambda: self.update("join"))
        self.m_createGroup.clicked.connect(lambda: self.update("create"))

    def update(self, option):
        if option=="join":
            self.m_joinGroup.setSelected(True)
            self.m_createGroup.setSelected(False)
            self.m_stack.setCurrentIndex(0)
        else:
            self.m_joinGroup.setSelected(False)
            self.m_createGroup.setSelected(True)
            self.m_stack.setCurrentIndex(1)



class Chat(QWidget):
    def __init__(self, groupname, chatID):
        super().__init__()

        self.m_onlineCount = 0
        self.m_members = {}
        self.m_stack = QStackedWidget()
        self.m_chatID = chatID
        self.m_chatView = ChatView(groupname)
        self.m_groupDescription = GroupDescription(groupname)

        self.m_stack.insertWidget(0, self.m_chatView)
        self.m_stack.insertWidget(1, self.m_groupDescription)


        self.m_layout = QVBoxLayout()

        self.m_layout.addWidget(self.m_stack)
        self.setLayout(self.m_layout)
        self.m_layout.setSpacing(0)
        self.m_layout.setContentsMargins(0,0,0,0)

        self.m_chatView.m_groupInfo.clicked.connect(self.switchChatView)
        self.m_groupDescription.m_groupDescriptionBar.m_button.mousePressEvent = lambda event: self.switchChatView()


    def switchChatView(self):
        index = self.m_stack.currentIndex()
        self.m_stack.setCurrentIndex(not index)
    
    
    def addMember(self, username, userID, admin, onlineStatus):
        self.m_members[username] = MemberInfo(username, admin, onlineStatus)
        self.m_groupDescription.m_membersBar.m_membersContainer.m_membersInfo[username] = self.m_members[username]
        self.m_groupDescription.m_membersBar.m_membersContainer.m_layout.addWidget(self.m_members[username])
    

    def changeMemberStatus(self, username, status):
        memberInfo = self.m_groupDescription.m_membersBar.m_membersContainer.m_membersInfo[username]
        if (status):
            memberInfo.m_state.setPixmap(memberInfo.m_onlinePixMap)
            self.m_onlineCount+=1
        else:
            memberInfo.m_state.setPixmap(memberInfo.m_offlinePixMap)
            self.m_onlineCount-=1




class ConfigBar(QWidget):
    def __init__(self):
        super().__init__()

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
                                background: qlineargradient(
                                spread:pad,
                                x1:0, y1:0, x2:0, y2:1, stop:0 #222831, stop:1 #393E46);
                                border-radius: 10px;
                                padding: 15px;
                                color: white; border-radius: 0;
                           """)

class UserConfigBar(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("UserConfigBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""
                           QWidget#UserConfigBar {
                                background: qlineargradient(
                                spread:pad,
                                x1:0, y1:0, x2:0, y2:1, stop:0 #222831, stop:1 #393E46);
                                border-radius: 10px;
                                padding: 15px;
                                color: white; border-radius: 0; }""")
    
        self.m_layout = QGridLayout()

        path = os.path.join("assets","user-icons/")

        self.icons = []

        for dir in os.listdir(path):
            btn = QPushButton()
            btn.setStyleSheet("background-color: #393E46; padding: 5px 0px;")
            btn.setContentsMargins(0,0,0,0)
            btn.setIcon(QIcon(path+dir))
            btn.setIconSize(QSize(32,32))
            self.icons.append(btn)
                
        for i in range(0, len(self.icons), 3):
            if i + 2 < len(self.icons):
                self.m_layout.addWidget(self.icons[i], i // 3, 0)
                self.m_layout.addWidget(self.icons[i + 1], i // 3, 1)
                self.m_layout.addWidget(self.icons[i + 2], i // 3, 2)

        self.setLayout(self.m_layout)