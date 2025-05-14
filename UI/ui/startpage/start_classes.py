from lib_QT.ImportQT import *

class inputField(QLineEdit):
    def __init__(self, placeholder):
        super().__init__()

        self.setMaximumWidth(300)
        self.setPlaceholderText(placeholder)
        self.setStyleSheet("""QLineEdit { 
                                padding: 10px; 
                                background-color: #222831;
                                border-radius: 10px;
                                outline: none;
                                color: white;
                            }

                            QLineEdit:focus {
                                border: 1px solid gray;
                                outline: none;
                            }""")

class hyperLink(QLabel):
    def __init__(self,text):
        super().__init__()
        self.setText(text)
        self.setStyleSheet("color: white; text-decoration: underline;")
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))


class buttonsContainer(QWidget):
    def __init__(self, section):
        super().__init__()

        self.m_layout = QHBoxLayout()
        self.m_layout.setAlignment(Qt.AlignCenter)

        self.setStyleSheet("""QPushButton { background-color: #948979; padding: 10px; color: #222831 }""")

        if (section=="login"):
            self.m_registerButton = hyperLink("Register")
            self.m_loginButton = QPushButton("Login")
        else:
            self.m_loginButton = hyperLink("Login")
            self.m_registerButton = QPushButton("Register")

        self.m_layout.addWidget(self.m_loginButton)
        self.m_layout.addWidget(self.m_registerButton)

        self.setLayout(self.m_layout)
        self.m_layout.setSpacing(30)


class LoginSection(QWidget):
    def __init__(self):
        super().__init__()

        self.m_buttonContainer = buttonsContainer("login")

        self.m_layout = QVBoxLayout()
        self.m_layout.setAlignment(Qt.AlignCenter)

        self.m_userInput = inputField("Username")
        self.m_passwordInput = inputField("Password")
        self.m_passwordInput.setEchoMode(QLineEdit.Password)

        icon = QIcon("assets/icons/Interface-Essential-Lock--Streamline-Pixel.svg")

        icon2 = QIcon("assets/icons/Interface-Essential-Profile-Male--Streamline-Pixel.svg")

        self.m_passwordInput.addAction(icon, QLineEdit.TrailingPosition)
        self.m_userInput.addAction(icon2, QLineEdit.TrailingPosition)

        self.m_layout.addWidget(self.m_userInput)
        self.m_layout.addWidget(self.m_passwordInput)
        self.m_layout.addWidget(self.m_buttonContainer)

        self.setLayout(self.m_layout)

class RegisterSection(QWidget):
    def __init__(self):
        super().__init__()   

        self.m_buttonContainer = buttonsContainer("register")

        self.m_layout = QVBoxLayout()
        self.m_layout.setAlignment(Qt.AlignCenter)

        self.m_userInput = inputField("Username")
        self.m_passwordInput = inputField("Password")
        self.m_passwordInput.setEchoMode(QLineEdit.Password)
        self.m_repeatPasswordInput = inputField("Repeat password")
        self.m_repeatPasswordInput.setEchoMode(QLineEdit.Password)

        icon = QIcon("assets/icons/Interface-Essential-Lock--Streamline-Pixel.svg")

        icon2 = QIcon("assets/icons/Interface-Essential-Profile-Male--Streamline-Pixel.svg")

        self.m_passwordInput.addAction(icon, QLineEdit.TrailingPosition)
        self.m_repeatPasswordInput.addAction(icon, QLineEdit.TrailingPosition)
        self.m_userInput.addAction(icon2, QLineEdit.TrailingPosition)

        self.m_layout.addWidget(self.m_userInput)
        self.m_layout.addWidget(self.m_passwordInput)
        self.m_layout.addWidget(self.m_repeatPasswordInput)
        self.m_layout.addWidget(self.m_buttonContainer)

        self.setLayout(self.m_layout)


class TitleSection(QWidget):
    def __init__(self):
        super().__init__()   

        self.m_title = QLabel()
        self.m_title.setPixmap(QPixmap("assets/icons/logo.png").scaled(300,300, Qt.KeepAspectRatio))
        #self.m_title.setPixmap(self.m_title.scaled(100, 100, Qt.KeepAspectRatio))
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


class StartPage(QWidget):
    def __init__(self):
        super().__init__()
        self.setObjectName("StartPage")  # Name the widget

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet(""" QWidget#StartPage {
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

        self.m_titleSection = TitleSection() # Title section

        self.m_mainSection = QWidget() # Register/Login section
        self.m_stack = QStackedWidget() # Main section layout

        self.m_loginSection = LoginSection()
        self.m_registerSection = RegisterSection()

        self.m_stack.insertWidget(0, self.m_loginSection)  # index 0
        self.m_stack.insertWidget(1, self.m_registerSection)   # index 1


        self.m_mainLayout = QHBoxLayout()
        self.m_mainLayout.addWidget(self.m_stack)
        # Set main section layout
        self.m_mainSection.setLayout(self.m_mainLayout)

        self.m_warning = QLabel()
        self.m_warning.setAlignment(Qt.AlignBottom)

        # Add title section and main section to the layout
        self.m_layout = QVBoxLayout()
        self.m_layout.addWidget(self.m_titleSection,2)
        self.m_layout.addWidget(self.m_mainSection,1)
        self.m_layout.addWidget(self.m_warning,1)
        # Set the layout
        self.setLayout(self.m_layout)
        
        # Switch from login to register section
        self.m_loginSection.m_buttonContainer.m_registerButton.mousePressEvent = lambda event: self.switch_layout(1)
         # Switch from register to login section
        self.m_registerSection.m_buttonContainer.m_loginButton.mousePressEvent = lambda event: self.switch_layout(0)


    def switch_layout(self, index):
        self.m_stack.setCurrentIndex(index)
    
    def set_warning(self, flag, text):
        self.m_warning.setText(text)
        if flag:
            self.m_warning.setStyleSheet("color: #40e215;")
        else:
            self.m_warning.setStyleSheet("color: #ff5454;")

    