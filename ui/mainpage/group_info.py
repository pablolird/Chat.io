from PySide6.QtCore import (
    QSize, 
    Qt, 
    Signal, 
    Signal)
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QWidget,
    QScrollArea,
    QSizePolicy
)
from PySide6.QtGui import (
    QIcon,
    QPixmap
)
import os

class GroupInfo(QWidget):
    clicked = Signal()  # Custom signal for click
    def __init__(self, groupName):
        super().__init__()
        self.setObjectName("GroupInfo")
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: #222831; color: white; padding: 10px;")

        #self.m_onlineUsers = ["Lol", "Roberto", "XD"]
        self.m_onlineUsers = []
        self.m_groupName = QLabel(groupName)
        self.m_groupName.setAlignment(Qt.AlignCenter)
        self.m_groupName.setStyleSheet("font-size: 24px; font-weight: bold; padding: 15px;")
        self.m_onlineUsersText = QLabel(", ".join(self.m_onlineUsers))

        self.m_layout = QVBoxLayout()

        self.m_layout.addWidget(self.m_groupName)
        self.m_layout.addWidget(self.m_onlineUsersText)

        self.setLayout(self.m_layout)


    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()


class MemberInfo(QWidget):
    def __init__(self, username, role, isConnected):
        super().__init__() 
        self.setObjectName("MemberInfo")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""MemberInfo:hover { background-color: #1f252d; }
                            MemberInfo { background-color: #222831; border: 1px solid grey; }
                           QLabel { border: none; background-color: transparent }""")

        self.m_username = QLabel(username)

        self.m_role = QLabel()
        self.m_state = QLabel()

        self.m_onlinePixMap = QPixmap(os.path.join("assets","icons","connected.svg")).scaled(24,24,Qt.KeepAspectRatio)
        self.m_offlinePixMap =QPixmap(os.path.join("assets","icons","disconnected.svg")).scaled(24,24,Qt.KeepAspectRatio)

        if (role=="admin"):
            self.m_role.setPixmap(QPixmap(os.path.join("assets","icons","Interface-Essential-Crown--Streamline-Pixel.svg")).scaled(24,24,Qt.KeepAspectRatio))
    
        if (isConnected):
            self.m_state.setPixmap(self.m_onlinePixMap)
        else:
            self.m_state.setPixmap(self.m_offlinePixMap)


        self.m_layout = QHBoxLayout()

        self.m_icon = QLabel()
        self.m_icon.setPixmap(QPixmap(os.path.join("assets","icons","Coding-Apps-Websites-Android--Streamline-Pixel.svg")).scaled(24,24,Qt.KeepAspectRatio))

        self.m_layout.addWidget(self.m_icon,1)
        self.m_layout.addWidget(self.m_username,20)
        self.m_layout.addWidget(self.m_role,1)
        self.m_layout.addWidget(self.m_state,1)

        self.setLayout(self.m_layout)


class MembersContainer(QWidget):
    def __init__(self):
        super().__init__()
        self.m_membersInfo = {}

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("border-radius: 15px; color: white;")

        self.m_layout = QVBoxLayout()
        self.m_layout.setAlignment(Qt.AlignTop)  # Align all member widgets to the top
        self.setLayout(self.m_layout)

        # ❗ Important: Let container grow only as needed
        sizePolicy = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
        self.setSizePolicy(sizePolicy)

class GroupInviteContainer(QWidget):
    def __init__(self):
        super().__init__() 

        self.setObjectName("GroupInviteContainer")

        self.setStyleSheet("""

                            QPushButton {
                                border: 1px solid #3bff6f;
                                background-color: #222831;
                                outline: none;
                                color: blue;
                                padding: 10px;
                                border-radius: 10px;
                            }
                                       
                            QPushButton::hover {
                                background-color: #3bff6f;
                            }
                           
                           QWidget { color: white; } """)

        self.m_layout = QHBoxLayout()

        self.m_inviteText = QLabel("Invitation ID: ")
        self.m_inviteText.setStyleSheet("color: #3bff6f")
        self.m_groupInvitationID = QLabel("9SDKL23Hhews4dh")
        self.m_groupInvitationID.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.m_groupInvitationID.setCursor(Qt.IBeamCursor)
        self.m_copy_button = QPushButton("Copy")
        self.m_copy_button.setCursor(Qt.PointingHandCursor)
        self.m_copy_button.clicked.connect(self.copy_text)

        self.m_layout.addWidget(self.m_inviteText)
        self.m_layout.addWidget(self.m_groupInvitationID)
        self.m_layout.addWidget(self.m_copy_button)
        self.setLayout(self.m_layout)
        self.m_layout.setAlignment(Qt.AlignCenter)

    def copy_text(self):
        QApplication.clipboard().setText(self.m_groupInvitationID.text())


class MembersBar(QWidget):
    def __init__(self):
        super().__init__() 
        self.setObjectName("MembersBar")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: transparent;")

        self.m_membersContainer = MembersContainer()

        # ➤ Wrap MembersContainer in a QScrollArea
        scrollArea = QScrollArea()
        scrollArea.setWidgetResizable(True)

        scrollArea.setStyleSheet("""
                                    QScrollArea {
                                        background-color: #393E46;
                                        border: 1px solid #15191e;
                                        border-radius: 5px;
                                        color: white;
                                    }

                                    QScrollBar:vertical {
                                        background: #222831;
                                        width: 10px;
                                        margin: 0px;
                                        border-radius: 5px;
                                    }

                                    QScrollBar::handle:vertical {
                                        background: #888;
                                        min-height: 20px;
                                        border-radius: 5px;
                                    }

                                    QScrollBar::handle:vertical:hover {
                                        background: #aaa;
                                    }

                                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                                        height: 0px;
                                    }
                                """)



        self.m_groupInviteContainer = GroupInviteContainer()

        self.m_layout = QVBoxLayout()
        self.m_layout.setContentsMargins(20, 20, 20, 20)
        self.m_layout.setSpacing(20)

        # ➤ Add scrollArea instead of direct membersContainer

        # Wrapper widget to center MembersContainer
        wrapper = QWidget()
        wrapperLayout = QVBoxLayout()
        wrapperLayout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)  # Align center horizontally, top vertically
        wrapperLayout.addWidget(self.m_membersContainer)
        wrapper.setLayout(wrapperLayout)

        scrollArea.setWidget(wrapper)

        self.m_layout.addWidget(scrollArea)
        self.m_layout.addWidget(self.m_groupInviteContainer)

        self.m_deleteGroupButton = QPushButton("Delete Group")
        self.m_deleteGroupButton.setStyleSheet("""
            QPushButton:focus {
                outline: none;
            }
            QPushButton {
                border: 1px solid #ff3333;
                background-color: #222831;
                outline: none;
                color: #ff3333;
                padding: 10px;
                border-radius: 10px;
            }                                      
            QPushButton::hover {
                background-color: #ff3333;
                color: #800000;
            }
        """)
        self.m_deleteGroupButton.setCursor(Qt.PointingHandCursor)
        self.m_deleteGroupButton.setMaximumWidth(self.width() * 0.3)

        buttonLayout = QHBoxLayout()
        buttonLayout.setAlignment(Qt.AlignHCenter)
        buttonLayout.addWidget(self.m_deleteGroupButton)
        self.m_layout.addLayout(buttonLayout)

        self.m_layout.setAlignment(Qt.AlignCenter)
        self.m_layout.addStretch()
        self.setLayout(self.m_layout)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.m_membersContainer.setMaximumWidth(self.width() * 0.8)

class GroupDescriptionBar(QWidget):
    def __init__(self, groupname):
        super().__init__() 

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background-color: transparent; color: white; padding: 10px;")

        self.m_button = QPushButton()
        self.m_button.setIcon(QIcon(os.path.join("assets","icons","Interface-Essential-Navigation-Left-Circle-2--Streamline-Pixel.svg")))
        self.m_button.setIconSize(QSize(28,28))

        self.m_button.setStyleSheet("""QPushButton:focus {
                                            border: none;
                                            outline: none;
                                        }
                                    QPushButton {
                                            border: none;
                                            outline: none;
                                        }""")

        self.m_button.setCursor(Qt.PointingHandCursor)

        self.m_groupName = QLabel(groupname)
        self.m_groupName.setStyleSheet("font-size: 24px; font-weight: bold;")
        self.m_groupName.setAlignment(Qt.AlignCenter)


        self.m_layout = QGridLayout()

        self.m_layout.addWidget(self.m_groupName, 0, 0, 1, 3)  # Span 3 columns, center in grid
        self.m_layout.addWidget(self.m_button, 0, 2, Qt.AlignRight)  # Place button in the last column, aligned right

        self.m_layout.setColumnStretch(0, 1)
        self.m_layout.setColumnStretch(1, 1)
        self.m_layout.setColumnStretch(2, 1)

        self.setLayout(self.m_layout)
        

class GroupDescription(QWidget):
    def __init__(self, groupname):
        super().__init__() 
        
        self.setObjectName("GroupDescription")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(""" QWidget#GroupDescription {
                            background: qlineargradient(
                                spread:pad,
                                x1:0, y1:0, x2:0, y2:1,
                                stop:0 #222831  ,
                                stop:1 #1d222a
                            );
                            border-radius: 10px;
                            padding: 10px;
                            color: white; border-radius: 0;
                        }""")
    
        self.m_layout = QVBoxLayout()
        self.m_layout.setSpacing(0)
        self.m_layout.setContentsMargins(0,0,0,0)

        self.m_membersBar = MembersBar()
        self.m_groupDescriptionBar = GroupDescriptionBar(groupname)

        self.m_layout.addWidget(self.m_groupDescriptionBar,3)
        self.m_layout.addWidget(self.m_membersBar, 22)

        self.setLayout(self.m_layout)
        #self.m_layout.setAlignment(Qt.AlignRight)

