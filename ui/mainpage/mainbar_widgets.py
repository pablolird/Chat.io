import os
from PySide6.QtCore import (
    QSize, 
    Qt, 
)
from PySide6.QtWidgets import (
    QPushButton,
    QVBoxLayout,
    QGridLayout,
    QWidget,
    QStackedWidget,
)
from PySide6.QtGui import QIcon
from ui.mainpage.chat_view import ChatView
from ui.mainpage.group_info import GroupDescription, MemberInfo


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

        self.m_joinGroup = addGroupsBarButton("assets/icons/Search-User--Streamline-Pixel.svg", "Join existing group")
        self.m_createGroup = addGroupsBarButton("assets/icons/User-Single-Aim--Streamline-Pixel.svg", "Create group")

        self.m_layout.addWidget(self.m_joinGroup)
        self.m_layout.addWidget(self.m_createGroup)

        self.setLayout(self.m_layout)
        self.m_layout.addStretch()
        self.setContentsMargins(9,9,9,9)



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

        path = "assets/user-icons/"

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