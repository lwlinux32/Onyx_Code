# Onyx Code

Onyx Code is an extensible AI coding assistant designed to offer a flexible, CLI-based alternative for AI-powered development.
## Core Features

- Interactive REPL Environment: High-speed interactive loop for AI-driven coding.
- Multiple Model Support: Support for OpenAI, Anthropic, Gemini, Mistral, Ollama, and more.
- File System Integration: Direct reading and writing capabilities for local files.
- Auto-Save Protocol: Intelligent file modification and saving via standard command patterns.
- MCP Integration Readiness: Structured to connect with Model Context Protocol servers.
- Fallback Intelligence: Built-in tools for web searching and information gathering.

## Installation

### Globally via Python (Recommended)
This makes `onyx-code` available in any directory (Windows, macOS, Linux).

1. Clone or download this repository.
  ```bash
   git clone https://github.com/lwlinux32/Onyx_Code
  ```
2. Open your terminal in the project directory.
  ```bash
    cd path/to/Onyx_Code
  ```
3. Run the following command:
   ```bash
   pip install -e .
   ```
4. Now you can run the tool from anywhere:
   ```bash
   onyx-code --config
   ```

#### Globall via Terminal(Only for linux)
  ```bash
alias onyx-code=python /path/to/Onyx_Code/onyx_code.py
  ```
### Local Dev Setup
If you do not want to install it globally:
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the script directly:
   ```bash
   python onyx_code.py --config
   ```

## Windows Compatibility
The `pip install -e .` command will automatically create an `onyx-code.exe` wrapper in your Python Scripts folder. Ensure that your Python Scripts directory (e.g., `C:\Python3x\Scripts`) is in your system **PATH**.

## Usage

Slash Commands:
- `/help`: List all available commands.
- `/read [path]`: Ingest a file into context.
- `/write [path] [content]`: Manually save content to a file.
- `/clear`: Clear terminal history.
- `/settings`: Reopen the configuration manager.

Available CLI Commands:
- `/config`: Interactively update provider and model settings.
- `/read [path]`: Load file content into the conversation.
- `/write [path]`: Save the last AI response to a file.
- `/clear`: Reset history and clear terminal.

## Architecture

Onyx Code utilizes a full-stack architecture with an Express.js backend providing secure file system proxies and AI model routing, and a React frontend optimized for a high-performance terminal experience. The Python component provides a standalone LiteLLM-powered engine for terminal enthusiasts.

#Note! 
Onyx_Code doesnt need to e configured by the first opening because it uses Ollama qwen3-coding-next:cloud so, but if you wish to configurate it, run "onyx-code --conf"


