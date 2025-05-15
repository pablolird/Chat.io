from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
)
from PySide6.QtGui import QIcon
import sys
import os

class iconButton(QWidget):
    def __init__(self, path, toolTip):
        super().__init__()

        self.m_layout = QVBoxLayout()

        self.m_button = QPushButton()
        self.m_button.setFixedSize(48, 48)
        self.m_button.setIcon(QIcon(path))
        self.m_button.setIconSize(QSize(32,32))
        self.m_button.setCursor(Qt.PointingHandCursor)
        self.m_button.setToolTip(toolTip)

        self.m_button.setStyleSheet("""
                                    QPushButton {
                                        border-radius: 24px;
                                        border: none;
                                    }

                                    QPushButton:focus {
                                            border: none;
                                            outline: none;
                                        }

                                    QPushButton:hover {
                                        background-color: #1f252d;
                                        
                                    }


                                    QWidget[selected="true"] {
                                        background-color:  red;  /* Selected color */
                                    }
                                    
                                    QToolTip {
                                        background-color: #DFD0B8;
                                        color: black;
                                        padding: 5px;
                                        font-size: 12px;
                                        font-family: Minecraft;
                                    }""")

        self.m_layout.addWidget(self.m_button)
        self.setLayout(self.m_layout)
    
    def setSelected(self, is_selected):
        self.setProperty("selected", is_selected)
        self.style().unpolish(self)
        self.style().polish(self)

class SideBar(QWidget):
    def __init__(self):
        super().__init__()

        self.m_layout = QVBoxLayout()
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("""border: none;
                           border-right: 2px solid #1f252d;
                           padding: 40px 5px;
                           background-color: #222831;""")

        self.m_btn_profile = iconButton(os.path.join("assets","icons","Single-User-Shield--Streamline-Pixel.svg"), "User Settings")
        self.m_btn_settings = iconButton(os.path.join("assets","icons","Interface-Essential-Setting-Cog--Streamline-Pixel.svg"), "General Settings")
        self.m_btn_groups = iconButton(os.path.join("assets","icons","Multiple-User--Streamline-Pixel-2.svg"), "Groups")
        self.m_btn_addGroup = iconButton(os.path.join("assets","icons","Interface-Essential-Global-Public--Streamline-Pixel.svg"), "Join/Create Group")
        
        self.m_layout.addWidget(self.m_btn_addGroup)
        self.m_layout.addWidget(self.m_btn_groups)
        self.m_layout.addWidget(self.m_btn_settings)
        self.m_layout.addWidget(self.m_btn_profile)
        self.m_layout.addStretch()

        self.setLayout(self.m_layout)
        self.m_layout.setContentsMargins(0,0,0,0)
        self.m_layout.setSpacing(0)
        self.m_layout.addStretch()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Main layout container
        main_widget = QWidget()
        main_layout = QHBoxLayout()

        # Sidebar
        sidebar = SideBar()

        # Main content area
        content = QLabel("Chat content here")
        content.setStyleSheet("background-color: white;")

        # Add to main layout
        main_layout.addWidget(sidebar)
        main_layout.addWidget(content)

        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
        self.setWindowTitle("Chat App")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
