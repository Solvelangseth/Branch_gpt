import sqlite3

DB_PATH = 'chat.db'

def get_connection():
    return sqlite3.connect(DB_PATH)

def insert_conversation(parent_id=None, title=""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversations (parent_id, title) VALUES (?, ?)",
        (parent_id, title)
    )
    conn.commit()
    convo_id = cursor.lastrowid
    conn.close()
    return convo_id

def insert_message(conversation_id, role, message_text):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO messages (conversation_id, role, message_text) VALUES (?, ?, ?)",
        (conversation_id, role, message_text)
    )
    conn.commit()
    conn.close()

def get_conversation_messages(conversation_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, message_text FROM messages WHERE conversation_id = ? ORDER BY timestamp",
        (conversation_id,)
    )
    messages = [{'role': role, 'content': message_text} for role, message_text in cursor.fetchall()]
    conn.close()
    return messages

def get_all_conversations():
    """Get all conversations"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, parent_id FROM conversations ORDER BY created_at DESC"
    )
    conversations = cursor.fetchall()
    conn.close()
    return conversations

def get_conversation_title(conversation_id):
    """Get the title of a conversation"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT title FROM conversations WHERE id = ?",
        (conversation_id,)
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else "Untitled"

def get_branches_for_conversation(conversation_id):
    """Get all branches for a given conversation"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title FROM conversations WHERE parent_id = ? ORDER BY created_at",
        (conversation_id,)
    )
    branches = cursor.fetchall()
    conn.close()
    return branches

def update_conversation_title(conversation_id, new_title):
    """Update the title of a conversation"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE conversations SET title = ? WHERE id = ?",
        (new_title, conversation_id)
    )
    conn.commit()
    conn.close()
    return True

def get_message_count(conversation_id):
    """Get the number of messages in a conversation"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT COUNT(*) FROM messages WHERE conversation_id = ?",
        (conversation_id,)
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_parent_id(conversation_id):
    """Get the parent_id of a conversation, if it exists"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT parent_id FROM conversations WHERE id = ?",
        (conversation_id,)
    )
    result = cursor.fetchone()
    conn.close()
    return result[0] if result and result[0] is not None else None
