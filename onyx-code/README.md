# Onyx Code

Onyx Code is an extensible AI coding assistant designed to offer a flexible, CLI-based alternative for AI-powered development. It features a professional terminal-inspired web interface and a robust Python-based CLI tool.

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
2. Open your terminal in the project directory.
3. Run the following command:
   ```bash
   pip install -e .
   ```
4. Now you can run the tool from anywhere:
   ```bash
   onyx-code --config
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

### Python CLI
Run the CLI directly or via your alias:
```bash
onyx-code --config
```

Available CLI Commands:
- `/config`: Interactively update provider and model settings.
- `/read [path]`: Load file content into the conversation.
- `/write [path]`: Save the last AI response to a file.
- `/clear`: Reset history and clear terminal.

## Architecture

Onyx Code utilizes a full-stack architecture with an Express.js backend providing secure file system proxies and AI model routing, and a React frontend optimized for a high-performance terminal experience. The Python component provides a standalone LiteLLM-powered engine for terminal enthusiasts.


If you wish to run `onyx-code` from any directory, you can use the provided setup script or create a wrapper.

### Installation via setup.py
1. Create a file named `setup.py` in the root:
```python
from setuptools import setup

setup(
    name='onyx-code',
    version='1.0.0',
    py_modules=['onyx_code'],
    entry_points={
        'console_scripts': [
            'onyx-code=onyx_code:main',
        ],
    },
    install_requires=[
        'prompt_toolkit',
        'litellm',
        'duckduckgo_search',
        'wikipedia',
        'requests',
        'mcp',
    ],
)
```
2. Run `pip install -e .`
3. Now you can use `onyx-code --config` anywhere.

