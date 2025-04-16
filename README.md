# ChatGPT Clone with Branching

This is a desktop chat application built using Python, PyQt5, SQLite, and OpenAI’s API. It is a simplified ChatGPT clone designed for personal use that allows you to engage in conversations with an AI. In addition, the app supports **branching**, so you can start side conversations from any message—preserving the original context while exploring alternative discussion paths.

## Features

- **Chat Interface:**  
  A clean and responsive GUI built with PyQt5.
  
- **AI Integration:**  
  Uses OpenAI's Chat API to generate responses.

- **Local Persistence:**  
  Conversations and messages are stored in a local SQLite database.

- **Branching Conversations:**  
  Create branches from any message (even far back in the conversation) by capturing highlighted text as direct context or injecting tokens into a new branch.

- **Dynamic Title Generation:**  
  Generates and updates conversation titles based on the first exchange.

## Installation

1. **Clone the Repository:**
   ```bash
   git clone git@github.com:Solvelangseth/Branch_gpt.git
   cd Graph_gpt
