from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QLineEdit, QPushButton, 
                           QHBoxLayout, QTabWidget, QScrollArea, QLabel, QFrame, QToolButton,
                           QMenu, QAction)
from PyQt5.QtCore import Qt, QSize, QPoint
from PyQt5.QtGui import QFont, QColor, QTextCursor
from utils.api_client import get_chat_response, generate_title_from_conversation
from db.database import (insert_message, insert_conversation, get_conversation_messages, 
                        get_branches_for_conversation, get_conversation_title,
                        update_conversation_title, get_message_count)
import threading
import markdown
import re

class BranchButton(QPushButton):
    """Custom button for displaying branches in the conversation"""
    def __init__(self, branch_id, branch_title):
        super().__init__(f"🔄 {branch_title}")
        self.branch_id = branch_id
        self.setStyleSheet("""
            background-color: #ffde59;
            border: 3px solid #000000;
            border-radius: 4px;
            padding: 10px;
            font-weight: bold;
            font-size: 13px;
            margin: 5px 8px;
            text-align: left;
            color: #000000;
            box-shadow: 3px 3px 0px #000000;
        """)
        # Set maximum width but allow wrapping text
        self.setMaximumWidth(300)
        self.setMinimumHeight(45)

class ChatTab(QWidget):
    def __init__(self, title, conversation_id=None, parent_window=None):
        super().__init__()
        self.conversation_id = conversation_id
        self.title = title
        self.parent_window = parent_window  # Reference to the main window for branch management
        self.parent_id = None  # Will be set if this is a branch
        self.current_highlighted_text = ""  # Store the currently highlighted text
        self.branch_popup_button = None  # Will hold a reference to the floating branch button
        self.init_ui()
        
        # Flag to track if this is the first exchange (for title generation)
        self.is_first_exchange = get_message_count(self.conversation_id) == 0 if self.conversation_id else True
        self.first_user_message = ""
        
        # Initialize Markdown extensions with code highlighting
        self.markdown_extensions = [
            'markdown.extensions.fenced_code',
            'markdown.extensions.codehilite',
            'markdown.extensions.tables',
            'markdown.extensions.nl2br'
        ]
        
        # Add custom CSS for code blocks and syntax highlighting
        self.code_css = """
        <style>
            code {
                background-color: #f0f0f0;
                border: 1px solid #ddd;
                border-radius: 3px;
                font-family: Consolas, "Liberation Mono", Menlo, Courier, monospace;
                padding: 2px 4px;
                color: #333;
            }
            pre {
                background-color: #1e1e1e;
                border: 2px solid #000;
                border-radius: 3px;
                box-shadow: 3px 3px 0px #000000;
                padding: 12px;
                margin: 10px 0;
                overflow-x: auto;
                position: relative;
            }
            pre code {
                background-color: transparent;
                border: none;
                color: #d4d4d4;
                display: block;
                font-family: Consolas, "Liberation Mono", Menlo, Courier, monospace;
                line-height: 1.5;
                padding: 0;
                white-space: pre;
            }
            .language-python { color: #569cd6; }
            .language-javascript { color: #f9e2af; }
            .language-html { color: #ce9178; }
            .language-css { color: #9cdcfe; }
            .codehilite { background-color: #1e1e1e; }
            .codehilite .c1 { color: #6A9955; } /* Comment */
            .codehilite .k { color: #569cd6; } /* Keyword */
            .codehilite .n { color: #d4d4d4; } /* Name */
            .codehilite .o { color: #d4d4d4; } /* Operator */
            .codehilite .p { color: #d4d4d4; } /* Punctuation */
            .codehilite .s { color: #ce9178; } /* String */
            .codehilite .na { color: #9cdcfe; } /* Name.Attribute */
            .codehilite .nb { color: #dcdcaa; } /* Name.Builtin */
            .codehilite .nc { color: #4ec9b0; } /* Name.Class */
            .codehilite .nf { color: #dcdcaa; } /* Name.Function */
            .codehilite .s2 { color: #ce9178; } /* String.Double */
        </style>
        """
        
        # Load existing messages if conversation_id exists
        if self.conversation_id:
            self.load_conversation_history()
            # Get parent_id if this is a branch
            self.check_if_branch()
        
        # Add CSS to chat log
        self.chat_log.document().setDefaultStyleSheet(self.code_css)

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Chat log - messages between user and assistant
        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: 3px solid #000000;
                border-radius: 4px;
                padding: 15px;
                font-size: 15px;
                line-height: 1.6;
                color: #000000;
                box-shadow: 5px 5px 0px #000000;
            }
        """)
        
        # Connect text selection change signal to handle highlighted text
        self.chat_log.selectionChanged.connect(self.handle_text_selection)
        
        layout.addWidget(self.chat_log)
        
        # Input area
        input_area = QWidget()
        input_area.setStyleSheet("background-color: transparent;")
        h_layout = QHBoxLayout(input_area)
        h_layout.setContentsMargins(0, 15, 0, 0)
        h_layout.setSpacing(15)
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Type your message...")
        self.input_field.setMinimumHeight(55)
        self.input_field.setStyleSheet("""
            QLineEdit {
                border: 3px solid #000000;
                border-radius: 4px;
                padding: 12px 15px;
                background-color: #ffffff;
                font-size: 15px;
                color: #000000;
                box-shadow: 5px 5px 0px #000000;
            }
            QLineEdit:focus {
                border-color: #000000;
                background-color: #fffaf0;
            }
        """)
        self.input_field.returnPressed.connect(self.send_message)
        h_layout.addWidget(self.input_field)
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        
        self.send_button = QPushButton("Send")
        self.send_button.setMinimumHeight(55)
        self.send_button.setMinimumWidth(100)
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #9ea1ff;
                border: 3px solid #000000;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
                color: #000000;
                font-size: 15px;
                box-shadow: 5px 5px 0px #000000;
            }
            QPushButton:hover {
                background-color: #8a8eff;
                transform: translate(-2px, -2px);
                box-shadow: 7px 7px 0px #000000;
            }
            QPushButton:pressed {
                transform: translate(0px, 0px);
                box-shadow: 3px 3px 0px #000000;
            }
        """)
        self.send_button.clicked.connect(self.send_message)
        
        self.branch_button = QPushButton("Branch Chat")
        self.branch_button.setMinimumHeight(55)
        self.branch_button.setMinimumWidth(120)
        self.branch_button.setStyleSheet("""
            QPushButton {
                background-color: #ffde59;
                border: 3px solid #000000;
                border-radius: 4px;
                padding: 10px 20px;
                font-weight: bold;
                color: #000000;
                font-size: 15px;
                box-shadow: 5px 5px 0px #000000;
            }
            QPushButton:hover {
                background-color: #ffd32a;
                transform: translate(-2px, -2px);
                box-shadow: 7px 7px 0px #000000;
            }
            QPushButton:pressed {
                transform: translate(0px, 0px);
                box-shadow: 3px 3px 0px #000000;
            }
        """)
        self.branch_button.clicked.connect(self.create_branch)
        
        button_layout.addWidget(self.send_button)
        button_layout.addWidget(self.branch_button)
        
        h_layout.addLayout(button_layout)
        layout.addWidget(input_area)
        
        # Set layout stretch factors
        layout.setStretchFactor(self.chat_log, 5)
        layout.setStretchFactor(input_area, 1)

    def check_if_branch(self):
        """Get parent_id if this is a branch conversation"""
        from db.database import get_parent_id
        self.parent_id = get_parent_id(self.conversation_id)

    def format_markdown(self, text):
        """Convert markdown text to HTML with syntax highlighting"""
        # Process code blocks with syntax highlighting
        html = markdown.markdown(text, extensions=self.markdown_extensions)
        return html
        
    def get_next_message_id(self):
        """Generate a unique ID for the next message"""
        if not hasattr(self, "_message_counter"):
            self._message_counter = 0
        self._message_counter += 1
        return self._message_counter

    def load_conversation_history(self):
        """Load existing messages from the database into the chat log"""
        messages = get_conversation_messages(self.conversation_id)
        for message in messages:
            message_id = self.get_next_message_id()
            if message['role'] == 'user':
                # Process user messages
                formatted_content = self.format_markdown(message['content'])
                self.chat_log.append(f"""<div id="msg-{message_id}" style="margin: 10px 0; padding: 12px; background-color: #f0f0f0; border: 2px solid #000000; border-radius: 4px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <b style="color:#000000; font-size: 15px;">User:</b>
                        <span class="message-options" data-id="{message_id}" data-role="user" style="cursor: pointer; font-weight: bold; color: #000;">⋮</span>
                    </div>
                    <div style="margin-top: 8px;">{formatted_content}</div>
                </div>""")
            else:
                # Process assistant messages with markdown support
                formatted_content = self.format_markdown(message['content'])
                self.chat_log.append(f"""<div id="msg-{message_id}" style="margin: 10px 0; padding: 12px; background-color: #e0f0ff; border: 2px solid #000000; border-radius: 4px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <b style="color:#000000; font-size: 15px;">Assistant:</b>
                        <span class="message-options" data-id="{message_id}" data-role="assistant" style="cursor: pointer; font-weight: bold; color: #000;">⋮</span>
                    </div>
                    <div style="margin-top: 8px;">{formatted_content}</div>
                </div>""")
        
        # Connect options menu after loading all messages
        self.connect_options_menu()

    def connect_options_menu(self):
        """Connect the options menu to all message option buttons"""
        self.chat_log.document().documentLayout().documentSizeChanged.connect(
            lambda: self.setup_message_options())

    def setup_message_options(self):
        """Setup event handlers for message option buttons"""
        # We need to use JavaScript to handle the click events for the message options
        script = """
        var optionElements = document.getElementsByClassName('message-options');
        for (var i = 0; i < optionElements.length; i++) {
            optionElements[i].onclick = function() {
                var messageId = this.getAttribute('data-id');
                var role = this.getAttribute('data-role');
                window.messageOptionClicked(messageId, role);
            };
        }
        """
        
        # This won't work directly since QTextEdit doesn't have full browser capabilities
        # Instead, we'll use mousePress and manually check for clicks on options
        self.chat_log.mousePressEvent = self.handle_chat_log_mouse_press

    def handle_chat_log_mouse_press(self, event):
        """Handle mouse press events in the chat log"""
        # Call the original mousePressEvent
        QTextEdit.mousePressEvent(self.chat_log, event)
        
        # Get the position and check if we clicked on a message option
        cursor = self.chat_log.cursorForPosition(event.pos())
        format = cursor.charFormat()
        
        # Check if the cursor is at a position with a message-options class
        if cursor.atBlockEnd() and "message-options" in self.chat_log.toHtml()[cursor.position()-30:cursor.position()+30]:
            # Determine which message was clicked by examining nearby HTML
            html_fragment = self.chat_log.toHtml()[max(0, cursor.position()-100):cursor.position()+100]
            
            # Try to extract message ID and role using simple pattern matching
            import re
            match = re.search(r'data-id="(\d+)" data-role="([^"]+)"', html_fragment)
            if match:
                message_id = match.group(1)
                message_role = match.group(2)
                
                # Show context menu at the current mouse position
                self.show_message_options_menu(event.globalPos(), message_id, message_role)

    def show_message_options_menu(self, position, message_id, message_role):
        """Show context menu for a message"""
        context_menu = QMenu(self)
        
        # Add branch action
        branch_action = QAction("Branch from this message", self)
        branch_action.triggered.connect(lambda: self.branch_from_message(message_id, message_role))
        context_menu.addAction(branch_action)
        
        # Execute the menu
        context_menu.exec_(position)

    def branch_from_message(self, message_id, message_role):
        """Create a branch starting from a specific message"""
        if not self.conversation_id:
            return
            
        # If this is already a branch, use its parent_id
        parent_id = self.parent_id if self.parent_id else self.conversation_id
        
        # Create a new branch title
        branch_title = f"Branch from message #{message_id}"
        new_convo_id = insert_conversation(parent_id=parent_id, title=branch_title)
        
        # Get the parent conversation's history
        all_messages = get_conversation_messages(self.conversation_id)
        
        # Only include messages up to and including the selected message
        # First, find the index of the selected message
        message_index = int(message_id) - 1  # Assuming IDs are sequential and 1-indexed
        message_index = min(message_index, len(all_messages) - 1)  # Safety check
        
        # Copy messages up to and including the selected message
        for i, message in enumerate(all_messages):
            if i <= message_index:
                insert_message(new_convo_id, message['role'], message['content'])
        
        # Check if parent window is available for tab management
        if not self.parent_window:
            self.chat_log.append("""<div style="margin: 10px 0; padding: 12px; background-color: #ffcccc; border: 2px solid #000000; border-radius: 4px;">
                <i style="color:#000000;"><b>Error:</b> Could not create branch - parent window not found</i>
            </div>""")
            return
        
        # Add the branch to parent's tab widget
        branch_tab = self.parent_window.add_branch_tab(parent_id, new_convo_id, branch_title)
        
        # Notify in the current tab that a branch was created
        self.chat_log.append(f"""<div style="margin: 15px 0; padding: 12px; background-color: #ffde59; border: 3px solid #000000; border-radius: 4px; box-shadow: 5px 5px 0px #000000;">
            <span style="color:#000000; font-weight: bold; font-size: 15px;">Branch created from message #{message_id}</span>
        </div>""")
        
        # Add a note to the new branch about its origin
        if branch_tab:
            branch_tab.chat_log.append(f"""<div style="margin: 15px 0; padding: 12px; background-color: #ffde59; border: 3px solid #000000; border-radius: 4px; box-shadow: 5px 5px 0px #000000;">
                <b style="color:#000000; font-size: 15px;">Branch Info:</b>
                <div style="margin-top: 8px;">This branch was created from message #{message_id} in the parent conversation.</div>
            </div>""")

    def send_message(self):
        message = self.input_field.text().strip()
        if message:
            # Format user message with markdown
            formatted_message = self.format_markdown(message)
            message_id = self.get_next_message_id()
            self.chat_log.append(f"""<div id="msg-{message_id}" style="margin: 10px 0; padding: 12px; background-color: #f0f0f0; border: 2px solid #000000; border-radius: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <b style="color:#000000; font-size: 15px;">User:</b>
                    <span class="message-options" data-id="{message_id}" data-role="user" style="cursor: pointer; font-weight: bold; color: #000;">⋮</span>
                </div>
                <div style="margin-top: 8px;">{formatted_message}</div>
            </div>""")
            self.input_field.clear()
            
            # Connect options menu to the newly added message
            self.connect_options_menu()
            
            # Store the first user message for title generation
            if self.is_first_exchange:
                self.first_user_message = message
            
            # Make sure we have a conversation_id
            if not self.conversation_id:
                self.conversation_id = insert_conversation(title=self.title)
            
            # Add the user message to the database
            insert_message(self.conversation_id, "user", message)
            
            # Retrieve the full conversation history including the latest message
            conversation_history = get_conversation_messages(self.conversation_id)
            
            # Show typing indicator
            typing_index = self.chat_log.document().characterCount()
            self.chat_log.append("""<div style="margin: 10px 0; padding: 12px; background-color: #e0f0ff; border: 2px dashed #000000; border-radius: 4px;">
                <i style="color:#000000;">Assistant is typing...</i>
            </div>""")
            
            # Start the API call in a separate thread to avoid UI freezing
            thread = threading.Thread(target=self.call_api, args=(conversation_history, typing_index, message))
            thread.start()

    def simulate_response(self, user_message):
        response = f"Simulated reply for: {user_message}"
        formatted_response = self.format_markdown(response)
        self.chat_log.append(f"""<div style="margin: 10px 0; padding: 12px; background-color: #e0f0ff; border: 2px solid #000000; border-radius: 4px;">
            <b style="color:#000000; font-size: 15px;">Assistant:</b>
            <div style="margin-top: 8px;">{formatted_response}</div>
        </div>""")

    def create_branch(self):
        # Need to have a conversation_id to branch from
        if not self.conversation_id:
            self.conversation_id = insert_conversation(title=self.title)
        
        # If this is already a branch, use its parent_id
        parent_id = self.parent_id if self.parent_id else self.conversation_id
        
        # Create a new conversation with the parent ID
        branch_title = f"Branch of {self.title}"
        new_convo_id = insert_conversation(parent_id=parent_id, title=branch_title)
        
        # Get the parent conversation's history
        parent_messages = get_conversation_messages(self.conversation_id)
        
        # Check if parent window is available for tab management
        if not self.parent_window:
            self.chat_log.append("""<div style="margin: 10px 0; padding: 12px; background-color: #ffcccc; border: 2px solid #000000; border-radius: 4px;">
                <i style="color:#000000;"><b>Error:</b> Could not create branch - parent window not found</i>
            </div>""")
            return
        
        # Copy messages to the new branch
        for message in parent_messages:
            insert_message(new_convo_id, message['role'], message['content'])
        
        # Add the branch to parent's tab widget
        self.parent_window.add_branch_tab(parent_id, new_convo_id, branch_title)
        
        # Notify in the current tab that a branch was created
        self.chat_log.append(f"""<div style="margin: 15px 0; padding: 12px; background-color: #ffde59; border: 3px solid #000000; border-radius: 4px; box-shadow: 5px 5px 0px #000000;">
            <span style="color:#000000; font-weight: bold; font-size: 15px;">Branch created: {branch_title}</span>
        </div>""")

    def call_api(self, conversation_history, typing_index=None, user_message=None):
        try:
            response = get_chat_response(conversation_history)
            
            # Remove typing indicator if it exists
            if typing_index is not None:
                cursor = self.chat_log.textCursor()
                cursor.setPosition(typing_index)
                cursor.movePosition(cursor.End, cursor.KeepAnchor)
                cursor.removeSelectedText()
            
            # Format assistant response with markdown
            formatted_response = self.format_markdown(response)
            message_id = self.get_next_message_id()
            self.chat_log.append(f"""<div id="msg-{message_id}" style="margin: 10px 0; padding: 12px; background-color: #e0f0ff; border: 2px solid #000000; border-radius: 4px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <b style="color:#000000; font-size: 15px;">Assistant:</b>
                    <span class="message-options" data-id="{message_id}" data-role="assistant" style="cursor: pointer; font-weight: bold; color: #000;">⋮</span>
                </div>
                <div style="margin-top: 8px;">{formatted_response}</div>
            </div>""")
            
            # Connect options menu to the newly added message
            self.connect_options_menu()
            
            # Double-check we have conversation_id before inserting
            if not self.conversation_id:
                self.conversation_id = insert_conversation(title=self.title)
            
            insert_message(self.conversation_id, "assistant", response)
            
            # Generate title after first exchange
            if self.is_first_exchange and user_message and self.conversation_id:
                self.is_first_exchange = False
                self.generate_and_update_title(user_message, response)
                
        except Exception as e:
            error_message = f"Error calling API: {str(e)}"
            print(error_message)
            
            # Remove typing indicator if it exists
            if typing_index is not None:
                cursor = self.chat_log.textCursor()
                cursor.setPosition(typing_index)
                cursor.movePosition(cursor.End, cursor.KeepAnchor)
                cursor.removeSelectedText()
            
            self.chat_log.append(f"""<div style="margin: 10px 0; padding: 12px; background-color: #ffcccc; border: 2px solid #000000; border-radius: 4px;">
                <b style="color:#000000; font-size: 15px;">Error:</b>
                <div style="margin-top: 8px;">{error_message}</div>
            </div>""")
    
    def generate_and_update_title(self, user_message, assistant_response):
        """Generate a title based on the first exchange and update the conversation"""
        if not self.conversation_id:
            return
        
        # Start a thread to generate the title
        thread = threading.Thread(target=self._generate_title_thread, args=(user_message, assistant_response))
        thread.start()
    
    def _generate_title_thread(self, user_message, assistant_response):
        """Thread function to generate and update the conversation title"""
        try:
            # Generate title using the API
            new_title = generate_title_from_conversation(user_message, assistant_response)
            
            # Update the database
            if new_title and new_title != "New Conversation" and new_title != "New Chat":
                update_conversation_title(self.conversation_id, new_title)
                self.title = new_title
                
                # Update in UI - find the tab widget containing this tab
                if self.parent_window:
                    if self.parent_id:
                        # This is a branch tab
                        if self.parent_id in self.parent_window.chat_tabs:
                            tab_widget = self.parent_window.chat_tabs[self.parent_id]
                            for i in range(tab_widget.count()):
                                if tab_widget.widget(i) == self:
                                    tab_widget.setTabText(i, new_title)
                                    break
                    else:
                        # This is a main tab
                        if self.conversation_id in self.parent_window.chat_tabs:
                            tab_widget = self.parent_window.chat_tabs[self.conversation_id]
                            # Update main tab text (usually at index 0)
                            if tab_widget.widget(0) == self:
                                tab_widget.setTabText(0, "Main")
                            
                        # Refresh sidebar to show updated title
                        self.parent_window.refresh_conversation_list()
                        
        except Exception as e:
            print(f"Error generating title: {str(e)}")

    def handle_text_selection(self):
        """Handle when text is selected/highlighted in the chat log"""
        cursor = self.chat_log.textCursor()
        if cursor.hasSelection():
            self.current_highlighted_text = cursor.selectedText()
            if len(self.current_highlighted_text) > 0:
                # Show the branch button near the selection
                self.show_branch_popup_button()
        else:
            self.current_highlighted_text = ""
            # Hide the branch button if no text is selected
            self.hide_branch_popup_button()
    
    def show_branch_popup_button(self):
        """Show a floating button near the text selection to create a branch"""
        if not self.branch_popup_button:
            # Create popup button if it doesn't exist
            self.branch_popup_button = QToolButton(self.chat_log)
            self.branch_popup_button.setText("Branch")
            self.branch_popup_button.setStyleSheet("""
                QToolButton {
                    background-color: #ffde59;
                    border: 2px solid #000000;
                    border-radius: 4px;
                    padding: 5px 8px;
                    font-weight: bold;
                    font-size: 12px;
                    color: #000000;
                    box-shadow: 3px 3px 0px #000000;
                }
                QToolButton:hover {
                    background-color: #ffd32a;
                    transform: translate(-2px, -2px);
                }
            """)
            self.branch_popup_button.clicked.connect(self.create_branch_from_selection)
        
        # Position the button near the current selection
        cursor = self.chat_log.textCursor()
        rect = self.chat_log.cursorRect(cursor)
        point = self.chat_log.mapToGlobal(QPoint(rect.right(), rect.top()))
        point = self.chat_log.mapFromGlobal(point)
        
        # Adjust position to be visible and not overlapping too much with the text
        self.branch_popup_button.move(point.x() + 10, point.y() - 30)
        self.branch_popup_button.show()
        self.branch_popup_button.raise_()
    
    def hide_branch_popup_button(self):
        """Hide the branch popup button"""
        if self.branch_popup_button:
            self.branch_popup_button.hide()
    
    def create_branch_from_selection(self):
        """Create a branch based on the currently highlighted text"""
        if not self.current_highlighted_text or not self.conversation_id:
            return
            
        # If this is already a branch, use its parent_id
        parent_id = self.parent_id if self.parent_id else self.conversation_id
        
        # Create a new conversation with the parent ID
        branch_title = f"Branch: {self.current_highlighted_text[:30]}..." if len(self.current_highlighted_text) > 30 else f"Branch: {self.current_highlighted_text}"
        new_convo_id = insert_conversation(parent_id=parent_id, title=branch_title)
        
        # Get the parent conversation's history
        parent_messages = get_conversation_messages(self.conversation_id)
        
        # Check if parent window is available for tab management
        if not self.parent_window:
            self.chat_log.append("""<div style="margin: 10px 0; padding: 12px; background-color: #ffcccc; border: 2px solid #000000; border-radius: 4px;">
                <i style="color:#000000;"><b>Error:</b> Could not create branch - parent window not found</i>
            </div>""")
            return
        
        # Copy messages to the new branch
        for message in parent_messages:
            insert_message(new_convo_id, message['role'], message['content'])
        
        # Add the branch to parent's tab widget
        branch_tab = self.parent_window.add_branch_tab(parent_id, new_convo_id, branch_title)
        
        # Notify in the current tab that a branch was created
        self.chat_log.append(f"""<div style="margin: 15px 0; padding: 12px; background-color: #ffde59; border: 3px solid #000000; border-radius: 4px; box-shadow: 5px 5px 0px #000000;">
            <span style="color:#000000; font-weight: bold; font-size: 15px;">Branch created with selected text</span>
        </div>""")
        
        # Add the highlighted text as context to the new branch
        if branch_tab:
            # Format the highlighted text specially
            formatted_highlight = self.current_highlighted_text
            
            # Check if it's code by looking for common patterns
            is_code = False
            if "```" in formatted_highlight or any(keyword in formatted_highlight for keyword in ["def ", "function", "class ", "import ", "from ", "var ", "const "]):
                is_code = True
            
            if is_code:
                # Format as code block with special styling
                branch_tab.chat_log.append(f"""<div style="margin: 15px 0; padding: 12px; background-color: #1e1e1e; border: 3px solid #000000; border-radius: 4px; box-shadow: 5px 5px 0px #000000;">
                    <b style="color:#ffffff; font-size: 15px;">Selected Code Context:</b>
                    <pre style="margin-top: 12px; padding: 15px; background-color: #2d2d2d; border: 2px solid #555; border-radius: 4px; color: #e0e0e0; font-family: monospace; font-size: 14px; overflow-x: auto;">{formatted_highlight}</pre>
                </div>""")
            else:
                # Format as regular text with special styling
                branch_tab.chat_log.append(f"""<div style="margin: 15px 0; padding: 12px; background-color: #e0f0ff; border: 3px solid #000000; border-radius: 4px; box-shadow: 5px 5px 0px #000000;">
                    <b style="color:#000000; font-size: 15px;">Selected Text Context:</b>
                    <div style="margin-top: 8px; padding: 10px; background-color: #fffbea; border: 2px solid #ffd32a; border-radius: 4px; font-style: italic; font-weight: bold;">{formatted_highlight}</div>
                </div>""")
        
        # Hide the popup button after creating the branch
        self.hide_branch_popup_button()

