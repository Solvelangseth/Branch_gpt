from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QTabWidget, QApplication, QHBoxLayout, QSplitter, QListWidget, QListWidgetItem, QPushButton, QLabel, QFrame, QStackedWidget)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QPalette, QColor
import sys
import os
from ui.main_window import ChatTab
from db.database import insert_conversation, get_all_conversations, get_conversation_title, get_branches_for_conversation, get_message_count
import markdown
import importlib.util

def check_dependencies():
    """Check if all required packages are installed"""
    required_packages = {
        "markdown": "markdown",
        "pygments": "pygments"
    }
    
    missing_packages = []
    for package_name, import_name in required_packages.items():
        spec = importlib.util.find_spec(import_name)
        if spec is None:
            missing_packages.append(package_name)
    
    if missing_packages:
        print(f"Missing required packages: {', '.join(missing_packages)}")
        print("Please install them using: pip install " + " ".join(missing_packages))
        return False
    return True

class ChatWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Branching Chat")
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #ffffff;
                font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', Arial, sans-serif;
            }
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #e1e1e1;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: 500;
                margin: 6px;
                color: #000000;
                font-size: 14px;
                position: relative;
            }
            QPushButton:hover {
                background-color: #f8f8f8;
                border-color: #d1d1d1;
            }
            QPushButton:pressed {
                background-color: #f0f0f0;
            }
            QListWidget {
                background-color: #ffffff;
                border: 1px solid #e1e1e1;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 12px;
                margin: 4px 0px;
                border: none;
                border-radius: 6px;
                background-color: #f8f8f8;
                color: #000000;
            }
            QListWidget::item:selected {
                background-color: #f0f0f0;
                color: #000000;
                font-weight: 500;
            }
            QTabWidget::pane {
                border: 1px solid #e1e1e1;
                border-radius: 8px;
                background-color: #ffffff;
            }
            QTabBar::tab {
                background-color: #ffffff;
                border: 1px solid #e1e1e1;
                border-bottom-color: transparent;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 16px;
                margin-right: 2px;
                font-weight: 500;
                color: #000000;
            }
            QTabBar::tab:selected {
                background-color: #f8f8f8;
            }
            QLineEdit {
                border: 1px solid #e1e1e1;
                border-radius: 8px;
                padding: 10px;
                background-color: #ffffff;
                font-size: 14px;
                color: #000000;
            }
            QTextEdit {
                border: 1px solid #e1e1e1;
                border-radius: 8px;
                padding: 15px;
                background-color: #ffffff;
                font-size: 14px;
                color: #000000;
            }
            QLabel {
                color: #000000;
                font-weight: 500;
            }
            QSplitter::handle {
                background-color: #e1e1e1;
                width: 1px;
            }
        """)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # Create a splitter for resizable sections
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - Conversation sidebar
        self.sidebar = QWidget()
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(10)
        
        # Header for sidebar
        sidebar_header = QLabel("Conversations")
        sidebar_header.setFont(QFont("-apple-system", 18, QFont.Medium))
        sidebar_header.setAlignment(Qt.AlignCenter)
        sidebar_header.setStyleSheet("""
            padding: 15px;
            background-color: transparent;
            color: #000000;
            margin-bottom: 10px;
            border-bottom: 1px solid #e1e1e1;
        """)
        sidebar_layout.addWidget(sidebar_header)
        
        # New Chat button
        new_chat_btn = QPushButton("+ New Chat")
        new_chat_btn.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-weight: 500;
                margin: 10px 5px;
                color: #ffffff;
                font-size: 15px;
            }
            QPushButton:hover {
                background-color: #0066DD;
            }
            QPushButton:pressed {
                background-color: #0055CC;
            }
        """)
        new_chat_btn.clicked.connect(self.create_new_chat)
        sidebar_layout.addWidget(new_chat_btn)
        
        # Empty state message
        self.empty_label = QLabel("No conversations yet.\nClick '+New Chat' to start.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet("""
            color: #666666;
            margin: 20px 0;
            font-size: 14px;
            padding: 20px;
            background-color: transparent;
            line-height: 1.6;
        """)
        sidebar_layout.addWidget(self.empty_label)
        
        # List of conversations
        self.conversation_list = QListWidget()
        self.conversation_list.itemClicked.connect(self.open_conversation)
        sidebar_layout.addWidget(self.conversation_list)
        
        # Initially hide the conversation list since it's empty
        self.conversation_list.setVisible(False)
        
        # Right side - Chat container with tabs for each branch
        self.chat_container = QStackedWidget()
        
        # Store open chat tabs
        self.chat_tabs = {}  # conversation_id -> QTabWidget
        
        # Add widgets to splitter
        splitter.addWidget(self.sidebar)
        splitter.addWidget(self.chat_container)
        
        # Set initial sizes
        splitter.setSizes([250, 750])
        
        main_layout.addWidget(splitter)
        
        # Welcome widget
        welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(welcome_widget)
        welcome_layout.setContentsMargins(40, 60, 40, 60)
        welcome_layout.setSpacing(30)
        
        welcome_label = QLabel("Welcome to Branching Chat")
        welcome_label.setFont(QFont("-apple-system", 32, QFont.Medium))
        welcome_label.setAlignment(Qt.AlignCenter)
        welcome_label.setStyleSheet("""
            color: #000000;
            margin: 20px 0;
            padding: 20px;
            background-color: transparent;
        """)
        
        instructions_label = QLabel("Start a new conversation and explore different paths through branching.\nCreate alternate discussion branches at any point to explore different directions.")
        instructions_label.setAlignment(Qt.AlignCenter)
        instructions_label.setStyleSheet("""
            color: #666666;
            font-size: 16px;
            margin: 15px 0;
            padding: 20px;
            background-color: transparent;
            line-height: 1.6;
        """)
        
        start_button = QPushButton("Start New Chat")
        start_button.setMinimumHeight(50)
        start_button.setMinimumWidth(200)
        start_button.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                border: none;
                border-radius: 25px;
                padding: 15px 30px;
                font-weight: 500;
                font-size: 16px;
                color: #ffffff;
                margin: 20px auto;
            }
            QPushButton:hover {
                background-color: #0066DD;
            }
            QPushButton:pressed {
                background-color: #0055CC;
            }
        """)
        start_button.clicked.connect(self.create_new_chat)
        
        welcome_layout.addStretch(1)
        welcome_layout.addWidget(welcome_label)
        welcome_layout.addWidget(instructions_label)
        welcome_layout.addWidget(start_button, 0, Qt.AlignCenter)
        welcome_layout.addStretch(1)
        
        # Add welcome widget to the container
        self.chat_container.addWidget(welcome_widget)
    
    def create_new_chat(self):
        """Create a new main conversation"""
        # Create a conversation in the database
        main_conversation_id = insert_conversation(title="New Chat")
        
        # Create a tab widget for this conversation
        tab_widget = QTabWidget()
        tab_widget.setTabsClosable(True)
        tab_widget.tabCloseRequested.connect(lambda index: self.close_branch_tab(tab_widget, index))
        
        # Create main chat tab
        main_tab = ChatTab("New Chat", conversation_id=main_conversation_id, parent_window=self)
        tab_widget.addTab(main_tab, "Main")
        
        # Store the tab widget
        self.chat_tabs[main_conversation_id] = tab_widget
        
        # Add to stacked widget and show it
        self.chat_container.addWidget(tab_widget)
        self.chat_container.setCurrentWidget(tab_widget)
        
        # Refresh sidebar
        self.refresh_conversation_list()
    
    def refresh_conversation_list(self):
        """Refresh the conversations list in the sidebar"""
        self.conversation_list.clear()
        conversations = get_all_conversations()
        
        has_conversations = False
        for convo_id, title, parent_id in conversations:
            # Only show parent conversations in the sidebar (no branches)
            if parent_id is None:
                has_conversations = True
                item = QListWidgetItem(f"{title}")
                item.setData(Qt.UserRole, convo_id)
                self.conversation_list.addItem(item)
        
        # Show/hide elements based on whether there are conversations
        self.conversation_list.setVisible(has_conversations)
        self.empty_label.setVisible(not has_conversations)
    
    def open_conversation(self, item):
        """Open a conversation when clicked in the sidebar"""
        conversation_id = item.data(Qt.UserRole)
        
        # Check if we already have a tab widget for this conversation
        if conversation_id in self.chat_tabs:
            # Show the existing tab widget
            self.chat_container.setCurrentWidget(self.chat_tabs[conversation_id])
        else:
            # Create a new tab widget for this conversation
            title = get_conversation_title(conversation_id)
            
            # Create tab widget
            tab_widget = QTabWidget()
            tab_widget.setTabsClosable(True)
            tab_widget.tabCloseRequested.connect(lambda index: self.close_branch_tab(tab_widget, index))
            
            # Create main chat tab
            main_tab = ChatTab(title, conversation_id=conversation_id, parent_window=self)
            tab_widget.addTab(main_tab, "Main")
            
            # Load branches for this conversation
            self.load_branches_as_tabs(conversation_id, tab_widget)
            
            # Store and show the tab widget
            self.chat_tabs[conversation_id] = tab_widget
            self.chat_container.addWidget(tab_widget)
            self.chat_container.setCurrentWidget(tab_widget)
    
    def load_branches_as_tabs(self, parent_conversation_id, tab_widget):
        """Load all branches for a conversation as tabs"""
        branches = get_branches_for_conversation(parent_conversation_id)
        
        for branch_id, branch_title in branches:
            branch_tab = ChatTab(branch_title, conversation_id=branch_id, parent_window=self)
            
            # Get message count to determine if this is a new branch or an existing one
            parent_message_count = get_message_count(parent_conversation_id)
            branch_message_count = get_message_count(branch_id)
            
            # If this branch only has copied messages from parent, mark as first exchange
            # But only if it has at least one message (otherwise it's completely empty)
            if branch_message_count > 0:
                # If parent and branch have the same number of messages,
                # this branch hasn't had its own conversation yet
                branch_tab.is_first_exchange = (branch_message_count == parent_message_count)
            
            # Add visual separator to indicate branch starting point
            branch_tab.chat_log.append("""<div style="margin: 20px 0; text-align: center;">
                <hr style="border: 2px solid #000000; margin: 10px 0;">
                <div style="background-color: #ffde59; padding: 12px; border: 3px solid #000000; border-radius: 4px; display: inline-block; margin: 10px auto; box-shadow: 5px 5px 0px #000000;">
                    <span style="color:#000000; font-weight: bold; font-size: 15px;">Branch created from parent conversation. New messages below:</span>
                </div>
                <hr style="border: 2px solid #000000; margin: 10px 0;">
            </div>""")
            
            tab_widget.addTab(branch_tab, branch_title)
    
    def add_branch_tab(self, parent_id, branch_id, branch_title):
        """Add a new branch tab to the parent conversation's tab widget"""
        if parent_id in self.chat_tabs:
            tab_widget = self.chat_tabs[parent_id]
            
            # We want branches to get proper titles after their first exchange
            # is_first_exchange should be true if branches are new
            branch_tab = ChatTab(branch_title, conversation_id=branch_id, parent_window=self)
            
            # Mark as a new conversation for title generation purposes
            # If there are no new messages beyond parent's messages
            branch_tab.is_first_exchange = True
            
            # Add visual separator to indicate branch starting point
            branch_tab.chat_log.append("""<div style="margin: 20px 0; text-align: center;">
                <hr style="border: 2px solid #000000; margin: 10px 0;">
                <div style="background-color: #ffde59; padding: 12px; border: 3px solid #000000; border-radius: 4px; display: inline-block; margin: 10px auto; box-shadow: 5px 5px 0px #000000;">
                    <span style="color:#000000; font-weight: bold; font-size: 15px;">Branch created from parent conversation. New messages below:</span>
                </div>
                <hr style="border: 2px solid #000000; margin: 10px 0;">
            </div>""")
            
            # Add the tab
            index = tab_widget.addTab(branch_tab, branch_title)
            tab_widget.setCurrentIndex(index)
            
            # Return the branch tab for further customization
            return branch_tab
            
        return None
    
    def close_branch_tab(self, tab_widget, index):
        """Close a branch tab"""
        # Don't close the main tab (index 0)
        if index > 0:
            tab_widget.removeTab(index)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    # Check if required dependencies are installed
    if not check_dependencies():
        sys.exit(1)
        
    window = ChatWindow()
    window.resize(1100, 750)
    window.show()
    sys.exit(app.exec_())
