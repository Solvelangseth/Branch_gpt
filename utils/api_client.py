import os
import requests
from dotenv import load_dotenv

load_dotenv()  # Loads variables from .env

API_KEY= os.getenv("OPENAI_API_KEY")
API_URL = "https://api.openai.com/v1/chat/completions"

def get_chat_response(conversation_history):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": conversation_history
    }
    response = requests.post(API_URL, headers=headers, json=data)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        print("Error from API:", response.text)
        return "Sorry, something went wrong."

def generate_title_from_conversation(user_message, assistant_response):
    """
    Generate a concise, descriptive title for a conversation based on the first 
    user message and assistant response.
    
    Args:
        user_message (str): The first message from the user
        assistant_response (str): The first response from the assistant
    
    Returns:
        str: A concise title for the conversation
    """
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Create a special prompt to generate a title
    messages = [
        {"role": "system", "content": "Generate a concise, descriptive title (3-6 words) for a conversation based on the user's question and assistant's response. Focus on the main topic or intent. Return only the title, no quotes or additional text."},
        {"role": "user", "content": f"User question: {user_message}\n\nAssistant response: {assistant_response}"}
    ]
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": messages,
        "max_tokens": 20,  # Limit to a short response
        "temperature": 0.7  # Slightly creative but not too random
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=data)
        if response.status_code == 200:
            title = response.json()['choices'][0]['message']['content'].strip()
            # Remove any quotes if present
            title = title.strip('"\'')
            return title
        else:
            print("Error generating title:", response.text)
            return "New Conversation"
    except Exception as e:
        print(f"Exception generating title: {str(e)}")
        return "New Conversation"
