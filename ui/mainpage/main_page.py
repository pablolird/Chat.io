from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QStackedWidget,
)

class MainBar(QWidget):

    def __init__(self):
        super().__init__()

        self.setStyleSheet("border-right: 1px solid #1f252d;")

        self.m_members = {"groupBar"   : 0, 
                          "addGroups"   : 1,
                          "config"      : 2,
                          "userConfig"  : 3}

        self.m_stack = QStackedWidget()

        self.m_groupBar = GroupBar()
        self.m_addGroups = addGroupsBar()
        self.m_config = ConfigBar()
        self.m_userConfig = UserConfigBar()

        self.m_stack.insertWidget(self.m_members["groupBar"]    , self.m_groupBar)
        self.m_stack.insertWidget(self.m_members["addGroups"]   , self.m_addGroups)
        self.m_stack.insertWidget(self.m_members["config"]      , self.m_config)
        self.m_stack.insertWidget(self.m_members["userConfig"]  , self.m_userConfig)

        self.m_layout = QVBoxLayout()
        self.m_layout.setContentsMargins(0,0,0,0)
        self.m_layout.setSpacing(0)
        self.m_layout.addWidget(self.m_stack)

        self.setLayout(self.m_layout)




class MainPage(QWidget):
    def __init__(self):
        super().__init__()


        self.m_chatsContainer = ChatsContainer()
        self.m_mainBar = MainBar()
        self.m_sidebar = SideBar()

        self.serverIDtoIndex = {}
        self.m_serverIDtoGroupBarIndex = {}

        self.setObjectName("MainPage")
        self.m_layout = QHBoxLayout()
        self.m_layout.addWidget(self.m_sidebar)     # Add main chat
        self.m_layout.addWidget(self.m_mainBar,1) # Add side bar of groups
        self.m_layout.addWidget(self.m_chatsContainer,2.5)     # Add main chat
        self.m_layout.setSpacing(0)
        self.m_layout.setContentsMargins(0,0,0,0)

        self.setLayout(self.m_layout)

        self.m_sidebar.m_btn_addGroup.m_button.clicked.connect(lambda: self.switchMainBar("addGroups"))
        self.m_sidebar.m_btn_groups.m_button.clicked.connect(lambda: self.switchMainBar("groupBar"))
        self.m_sidebar.m_btn_profile.m_button.clicked.connect(lambda: self.switchMainBar("userConfig"))
        self.m_sidebar.m_btn_settings.m_button.clicked.connect(lambda: self.switchMainBar("config"))

        self.m_mainBar.m_addGroups.m_createGroup.clicked.connect(lambda: self.switchToGroup(1))
        self.m_mainBar.m_addGroups.m_joinGroup.clicked.connect(lambda: self.switchToGroup(2))

    def switchToGroup(self, index):
        self.m_chatsContainer.m_stack.setCurrentIndex(index)

        for g in self.m_mainBar.m_groupBar.m_groups:
            g.setSelected(False)
        
        self.m_mainBar.m_addGroups.m_createGroup.setSelected(index==1)
        self.m_mainBar.m_addGroups.m_joinGroup.setSelected(index==2)

        
    def switchMainBar(self, key):
        self.m_mainBar.m_stack.setCurrentIndex(self.m_mainBar.m_members[key])

        self.m_sidebar.m_btn_addGroup.setSelected(key=="addGroups")
        self.m_sidebar.m_btn_groups.setSelected(key=="groupBar")
        self.m_sidebar.m_btn_profile.setSelected(key=="userConfig")
        self.m_sidebar.m_btn_settings.setSelected(key=="config")