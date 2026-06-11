# 🐉 Tatsu AI — Your Local Assistant

Welcome to Tatsu! This is a powerful, Jarvis-style AI assistant built for your Windows desktop. 
Tatsu can manage your files, remember things about you, execute terminal commands, and talk to you through a beautiful web dashboard.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
You must have **Python** installed on your computer. If you don't have it, download it from [python.org](https://www.python.org/downloads/) and ensure you check the box that says *"Add python.exe to PATH"* during installation.

### 2. Installation
Just double-click the **`install.bat`** file in this folder. It will automatically download all the required background packages.

### 3. Running Tatsu
Double-click the **`run.bat`** file. 
A terminal window will open to run the server, and your browser will automatically open the Tatsu Dashboard!

### 4. Logging In
When the dashboard opens, you will see a login screen. 
**The default password is: `admin123`**

---

## ⚙️ Configuration (Crucial Step)

Tatsu needs an "AI Brain" to function. Open the **`config.py`** file in Notepad or any text editor to choose how you want to run it. Go to line 31:

### Option A: Free Local Brain (Requires a good PC)
If you have a decent graphics card and want it to be 100% free and private:
1. Download and install [Ollama](https://ollama.com/).
2. Open your terminal and run: `ollama run qwen2.5:7b` (or whichever model you prefer).
3. In `config.py`, ensure:
   `LLM_PROVIDER = "ollama"`
   `OLLAMA_MODEL = "qwen2.5:7b"`

### Option B: Cloud Brain (Fast, requires an API Key)
If your PC is slower, you can use the Cloud:
1. In `config.py`, change it to:
   `LLM_PROVIDER = "openai"`
2. Get a free API key from [Groq](https://console.groq.com) or [NVIDIA](https://build.nvidia.com) (or use an OpenAI ChatGPT key).
3. Paste it in `config.py`:
   `OPENAI_API_KEY = "your-api-key-here"`
   `OPENAI_BASE_URL = "https://api.groq.com/openai/v1"` (change this based on your provider)
   `OPENAI_MODEL = "llama3-8b-8192"`

---

## 🛠️ What can Tatsu do?
Once you are in the chat dashboard, try asking Tatsu to:
- *"What is my CPU and RAM usage right now?"*
- *"Create a folder on my Desktop called SecretFiles."*
- *"Remember that my favorite food is Pizza."* (It will save this to a permanent vector database and remember it forever).
- *"Open YouTube and search for Lo-Fi Music."*

Enjoy your new AI assistant!
