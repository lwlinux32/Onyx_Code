import os
import sys
import json
import argparse
import subprocess
import requests
import time
import random
import re
from typing import List, Dict, Optional, Any
from datetime import datetime

# Third party imports
try:
    from prompt_toolkit import PromptSession, print_formatted_text
    from prompt_toolkit.styles import Style
    from prompt_toolkit.formatted_text import HTML, FormattedText
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
    import litellm
    from duckduckgo_search import DDGS
    import anyio
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
except ImportError as e:
    print(f"Error: Missing dependencies. Please run 'pip install -r requirements.txt'")
    print(f"Missing: {e.name}")
    sys.exit(1)

import shlex

# --- MCP Client Implementation ---

# --- Web Clone Skill Implementation ---

class WebCloneSkill:
    """A multi-phase pipeline skill for website cloning."""

    def __init__(self, output_prefix: str = "clone"):
        self.output_prefix = output_prefix

    def run_clone_pipeline(self, url: str, options: dict = None):
        """Execute the multi-phase website clone pipeline."""
        if options:
            self.clone_data.update(options)

        base_dir = f"./{self.output_prefix}_{url.replace('https://', '').replace('/', '_')}"
        if not os.path.exists(base_dir):
            os.makedirs(base_dir)

        print(f"\n[CLONE-WEBSITE] Starting clone pipeline for: {url}")
        print(f"  Output directory: {base_dir}")

        # Phase 1: Fetch HTML
        print("\n--- PHASE 1: FETCH ---")
        self._fetch_html(url, base_dir)
        size = os.path.getsize(os.path.join(base_dir, 'index.html')) if os.path.exists(os.path.join(base_dir, 'index.html')) else 0
        print(f"  [✓] Downloaded {size} chars")

        # Phase 2: Extract CSS
        print("\n--- PHASE 2: CSS ---")
        self._extract_css(url, base_dir)

        # Phase 3: Scaffolding
        print("\n--- PHASE 3: SCAFFOLD ---")
        self._create_scaffolding(base_dir)

        # Phase 4: Package
        print("\n--- PHASE 4: PACKAGE ---")
        self._create_package(base_dir, url)

        print("\n--- PHASE 5: CLAUDE.md ---")
        self._create_claude_md(base_dir, url)

        print(f"\n[CLONE-WEBSITE] Clone complete! Output in: {base_dir}/")
        return base_dir

    def _fetch_html(self, url: str, base_dir: str):
        """Phase 1: Download HTML."""
        try:
            import requests
            resp = requests.get(url, timeout=10)
            html = resp.text[:200000]  # First 200KB

            with open(os.path.join(base_dir, "index.html"), 'w', encoding='utf-8') as f:
                f.write(html)

            # Extract and save title
            title_start = html.find("<title>") + 7
            title_end = html.find("</title>")
            if title_start > 0 and title_end > title_start:
                title = html[title_start:title_end]
                with open(os.path.join(base_dir, "title.txt"), 'w') as f:
                    f.write(title.strip())

        except Exception as e:
            with open(os.path.join(base_dir, "index.html"), 'w') as f:
                f.write(f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{url}</title></head><body><h1>Cloned site: {url}</h1></body></html>")

    def _extract_css(self, url: str, base_dir: str):
        """Phase 2: Extract inline CSS."""
        try:
            import requests
            resp = requests.get(url, timeout=10)
            html = resp.text

            # Find <style> blocks
            css_blocks = []
            start = 0
            while True:
                idx = html.find("<style", start)
                if idx == -1:
                    break
                end = html.find("</style>", idx)
                if end != -1:
                    css = html[idx+7:end]
                    css_blocks.append(css)
                    start = end + 8

            if css_blocks:
                css_content = "\n\n".join(css_blocks)
                with open(os.path.join(base_dir, "styles.css"), 'w') as f:
                    f.write(f"/* Extracted CSS from {url} */\n{css_content}")
            else:
                # Generate minimal CSS
                css = f"body {{ margin: 0; font-family: system-ui; }}\n{url} {{ color: #1d4ed8; }}"
                with open(os.path.join(base_dir, "styles.css"), 'w') as f:
                    f.write(css)

        except Exception:
            css = f"/* Minimal CSS for {url} */\nbody {{ margin: 0; }}\nh1 {{ color: #1d4ed8; }}"
            with open(os.path.join(base_dir, "styles.css"), 'w') as f:
                f.write(css)

    def _create_scaffolding(self, base_dir: str):
        """Phase 3: Create config files."""
        files = {
            "package.json": '{"name": "clone", "version": "1.0.0", "type": "module"}',
            "tsconfig.json": '{"compilerOptions": {"target": "ES2020", "module": "ESNext"}}',
            "tailwind.config.js": 'module.exports = { content: ["./index.html"] };',
            "postcss.config.js": 'module.exports = { plugins: { tailwindcss: {} } };',
        }
        for fname, content in files.items():
            with open(os.path.join(base_dir, fname), 'w') as f:
                f.write(content)

    def _create_package(self, base_dir: str, url: str = None):
        """Phase 4: Create README."""
        url = url or self.clone_data.get('url') or 'example.com'
        readme = f"""# Cloned from {url}

Cloned website from: {url}

Files:
- `index.html` - Main HTML content
- `styles.css` - Extracted CSS
- `title.txt` - Page title

To view: Open `index.html` in a browser or use:
  npx serve .
"""
        with open(os.path.join(base_dir, "README.md"), 'w') as f:
            f.write(readme)

    def _create_claude_md(self, base_dir: str, url: str):
        """Phase 5: Create CLAUDE.md for Claude Code."""
        import datetime
        # Get title
        title_file = os.path.join(base_dir, "title.txt")
        if os.path.exists(title_file):
            with open(title_file) as f:
                title = f.read().strip()
        else:
            title = "Cloned Website"

        claude_md = f"""# Cloned Website: {title}

This directory contains a cloned version of:

**URL:** {url}

**Files:**
- `index.html` - Full HTML snapshot
- `styles.css` - Extracted CSS
- `title.txt` - Page title

## Quick Start

### View the site
```bash
cd {base_dir}
open index.html  # macOS
# or
xdg-open index.html  # Linux
```

### Inspect with Onyx Code
```bash
python /home/mert/onyx-code/onyx_code.py << 'EOF'
/read {os.path.join(base_dir, 'index.html')}
/exit
EOF
```

### Analyze the HTML
```bash
# Count links
grep -o 'href="[^"]*"' index.html | wc -l

# Extract images
grep -o 'img src="[^"]*"' index.html > images.txt

# Extract scripts
grep -o 'script src="[^"]*"' index.html > scripts.txt
```

**Generated:** {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")}
**Size:** {os.path.getsize(os.path.join(base_dir, 'index.html'))} bytes

Generated by Onyx Code WebCloneSkill
""".format(base_dir=base_dir)

        with open(os.path.join(base_dir, "CLAUDE.md"), 'w') as f:
            f.write(claude_md)
        print(f"  [✓] Created CLAUDE.md")


# Update tool description


# Update tool description

# --- MCP Client Implementation ---

class OnyxMCP:
    def __init__(self, command: str):
        self.command = command
        # Use shlex to correctly parse command strings with spaces/quotes
        self.parts = shlex.split(command)
        self.tools = []

    async def get_tools(self):
        if not self.parts: return []
        params = StdioServerParameters(command=self.parts[0], args=self.parts[1:])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                tools = await session.list_tools()
                self.tools = tools.tools
                return self.tools

    async def call_tool(self, name: str, arguments: dict):
        if not self.parts: return "No MCP command configured."
        params = StdioServerParameters(command=self.parts[0], args=self.parts[1:])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments)
                
                # Format result content into string
                output = []
                for item in result.content:
                    if hasattr(item, 'text'):
                        output.append(item.text)
                    elif hasattr(item, 'data'):
                        output.append(f"[Binary/Image Data]")
                    else:
                        output.append(str(item))
                return "\n".join(output)

# --- Constants ---
CONFIG_FILE = os.path.expanduser("~/.onyx_config.json")
HISTORY_FILE = os.path.expanduser("~/.onyx_history")
PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")

DEFAULT_PROMPT_FILE = "elite_architect.txt"

def get_available_prompts():
    if not os.path.exists(PROMPTS_DIR):
        os.makedirs(PROMPTS_DIR, exist_ok=True)
    return sorted([f for f in os.listdir(PROMPTS_DIR) if f.endswith(".txt")])

def load_prompt_content(filename):
    path = os.path.join(PROMPTS_DIR, filename)
    if os.path.exists(path):
        with open(path, 'r') as f:
            return f.read()
    return "You are Onyx Code, an elite AI coding assistant."

BANNER = """
 ██████╗ ███╗   ██╗██╗   ██╗██╗  ██╗     ██████╗ ██████╗ ██████╗ ███████╗
██╔═══██╗████╗  ██║╚██╗ ██╔╝╚██╗██╔╝    ██╔════╝██╔═══██╗██╔══██╗██╔════╝
██║   ██║██╔██╗ ██║ ╚████╔╝  ╚███╔╝     ██║     ██║   ██║██║  ██║█████╗  
██║   ██║██║╚██╗██║  ╚██╔╝   ██╔██╗     ██║     ██║   ██║██║  ██║██╔══╝  
╚██████╔╝██║ ╚████║   ██║   ██╔╝ ██╗    ╚██████╗╚██████╔╝██████╔╝███████╗
 ╚═════╝ ╚═╝  ╚═══╝   ╚═╝   ╚═╝  ╚═╝     ╚═════╝ ╚═════╝ ╚══════╝╚══════╝
                            [ v1.1.0 | AGENTIC AI CORE ]
"""

STYLE = Style.from_dict({
    'prompt': '#7c3aed bold',
    'command': '#a78bfa italic',
    'info': '#38bdf8',
    'error': '#f43f5e bold',
    'success': '#10b981',
    'system': '#71717a italic',
    'thought': '#94a3b8 italic',
    'banner': '#3b82f6 bold',
    'execution': '#c084fc bold',
})

# --- Internal Tools ---

# --- Web Clone Tool Definition ---
WEB_CLONE_TOOL = {
    "type": "function",
    "function": {
        "name": "clone-website",
        "description": "Point it at a URL, run the clone-website skill, and Onyx Code will inspect the site via Chrome MCP, extract design tokens and assets, write component specs, and dispatch parallel builder agents to reconstruct every section — all in isolated git worktrees that merge automatically.\n\nPhases:\n1. **Reconnaissance**: Inspect the target site via Chrome MCP to extract design tokens and assets.\n2. **Foundation**: Create isolated git worktree and scaffolding files (package.json, tsconfig.json, tailwind.config.js).\n3. **Component Specs**: Analyze and write component specs for every section.\n4. **Parallel Build**: Dispatch parallel builder agents to reconstruct sections.\n5. **Assembly & QA**: Merge worktrees, validate, optimize, and ensure pixel-perfect fidelity.\n\nConfiguration: Edit **TARGET.md** before running for fine-grained control over Pages, Fidelity, Scope, and Customization plans.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The target website URL to clone (e.g., 'https://example.com')."
                },
                "pages": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Which pages to replicate (default: home page).",
                    "default": ["home"]
                },
                "fidelity": {
                    "type": "string",
                    "description": "Clone fidelity level: 'pixel-perfect', 'high-fidelity', or 'structural'.",
                    "default": "pixel-perfect"
                },
                "scope": {
                    "type": "string",
                    "description": "What's in/out of scope (e.g., 'all', 'core-only').",
                    "default": "all"
                },
                "customization": {
                    "type": "string",
                    "description": "Modifications to apply after the base clone.",
                    "default": None
                }
            },
            "required": ["url"]
        }
    }
}


def get_internal_tools():
    return [
        WEB_CLONE_TOOL,
        {
            "type": "function",
            "function": {
                "name": "run_command",
                "description": "Execute a shell command in the terminal. Use this for creating directories, running builds, tests, or other CLI tasks.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The shell command to execute."
                        }
                    },
                    "required": ["command"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "write_file",
                "description": "Write or overwrite a file with specified content.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path to the file (e.g., workspace/app.py)."
                        },
                        "content": {
                            "type": "string",
                            "description": "The full content to write into the file."
                        }
                    },
                    "required": ["path", "content"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the contents of a file.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path to the file to read."
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_dir",
                "description": "List files and directories in a given path.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "The path to list (default is current directory).",
                            "default": "."
                        }
                    }
                }
            }
        }
    ]

# --- Core Logic ---

class OnyxCode:
    def __init__(self):
        self.config = self.load_config()
        self.provider = self.config.get("provider", "gemini")
        self.model = self.config.get("model", "gemini-2.0-flash")
        self.api_key = self.config.get("api_key", "")
        self.endpoint = self.config.get("endpoint", "")
        self.prompt_file = self.config.get("prompt_file", DEFAULT_PROMPT_FILE)
        self.mcp_command = self.config.get("mcp_command", "")
        
        content = load_prompt_content(self.prompt_file)
        # Added Internal Tool Documentation to System Prompt
        internal_tool_desc = """
CRITICAL: You are an agentic AI. When the user asks to create, modify, or save a file, you MUST use the provided tools to actually perform the action. 
Do not just show the code in a block; SAVE IT using write_file.

If your environment does not support native tool calling, output your tool request as a JSON block:
```json
{
  "name": "tool_name",
  "arguments": { "arg1": "val1" }
}
```

BUILT-IN TOOLS:
- write_file(path, content): Create or update files. Use 'workspace/' folder for all user projects.
- run_command(command): Execute shell commands (mkdir, npm, python, etc). Requires user confirmation.
- read_file(path): Read file contents.
- list_dir(path): List files in directory.
- clone-website(url, options): Clone a website via Chrome MCP. See /clone-website for usage.
"""
        self.history = [{"role": "system", "content": content + "\n\n" + internal_tool_desc}]
        
        self.mcp_client = OnyxMCP(self.mcp_command) if self.mcp_command else None
        
        self.session = PromptSession(
            history=FileHistory(HISTORY_FILE),
            auto_suggest=AutoSuggestFromHistory(),
            style=STYLE
        )
        
        if self.mcp_command:
            try:
                tools = anyio.run(self.mcp_client.get_tools)
                tool_desc = "\n".join([f"- {t.name}: {t.description}" for t in tools])
                self.history[0]["content"] += f"\n\nAVAILABLE MCP TOOLS:\n{tool_desc}\nProtocol: [USE_TOOL:name{{args}}]"

                # If using Chrome MCP, add the web clone tool
                if "chrome" in self.mcp_command.lower() or "chromium" in self.mcp_command.lower():
                    self.history[0]["content"] += f"\n\nWEB CLONE TOOL (Chrome MCP):\n  - clone-website: Clone websites via Chrome MCP.\n    See /clone-website for usage.\nProtocol: [CLONE-WEBSITE:url[options]]"
            except Exception as e:
                print(f"[ERROR] MCP Connection Failed: {str(e)}")

        self.apply_provider_settings()

    def load_config(self) -> dict:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        return {}

    def save_config(self):
        config_data = {
            "provider": self.provider,
            "model": self.model,
            "api_key": self.api_key,
            "endpoint": self.endpoint,
            "prompt_file": self.prompt_file,
            "mcp_command": self.mcp_command
        }
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=4)
        self.log(f"Configuration saved to {CONFIG_FILE}", "success")

    def apply_provider_settings(self):
        env_map = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "gemini": "GEMINI_API_KEY",
            "mistral": "MISTRAL_API_KEY",
            "groq": "GROQ_API_KEY",
        }
        
        effective_key = self.api_key if self.api_key else "sk-onyx-dummy-key"
        
        if self.provider in env_map:
            os.environ[env_map[self.provider]] = self.api_key if self.api_key else ""
        
        if self.provider == "local":
            self.log(f"Routing to local server at {self.endpoint or 'http://localhost:8080'}", "system")
            os.environ["OPENAI_API_KEY"] = effective_key

    def log(self, msg: str, status="info"):
        print_formatted_text(HTML(f"<{status}>[{status.upper()}] {msg}</{status}>"), style=STYLE)

    def configure_interactively(self):
        print("\n--- ONYX CODE CONFIGURATION ---")
        providers = ["anthropic", "openai", "gemini", "local", "ollama"]
        print(f"Supported providers: {', '.join(providers)}")
        self.provider = input(f"Select Provider [{self.provider}]: ").strip() or self.provider
        self.api_key = input("Enter API Key (if required): ").strip() or self.api_key
        self.model = input(f"Enter Model ID [{self.model}]: ").strip() or self.model
        endpoint_hint = "http://localhost:11434" if self.provider == "ollama" else "http://localhost:8080/v1"
        self.endpoint = input(f"Enter Local/Custom Endpoint (e.g. {endpoint_hint}) [{self.endpoint}]: ").strip() or self.endpoint
        self.mcp_command = input(f"MCP Server Command (e.g. npx -y @mcp/server-filesystem) [{self.mcp_command}]: ").strip() or self.mcp_command
        
        print("\n--- SELECT SYSTEM PROMPT ---")
        available = get_available_prompts()
        for idx, filename in enumerate(available):
            print(f"[{idx}] {filename}")
        
        choice_idx = input(f"Select Prompt Index (0-{len(available)-1}) [Current: {self.prompt_file}]: ").strip()
        if choice_idx:
            try:
                self.prompt_file = available[int(choice_idx)]
                content = load_prompt_content(self.prompt_file)
                self.history = [{"role": "system", "content": content}]
            except (ValueError, IndexError):
                self.log("Invalid selection, keeping current prompt.", "error")
        
        self.save_config()
        self.apply_provider_settings()

    def handle_command(self, user_input: str):
        parts = user_input.split()
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd == "/help":
            self.show_help()
        elif cmd == "/config":
            self.configure_interactively()
        elif cmd == "/init":
            self.init_workspace()
        elif cmd == "/version":
            self.show_version()
        elif cmd == "/stats":
            self.show_stats()
        elif cmd == "/list":
            if args:
                self.list_path(args[0])
            else:
                self.list_path(".")
        elif cmd == "/tree":
            if args:
                self.show_tree(args[0], depth=3)
            else:
                self.show_tree(".", depth=3)
        elif cmd == "/search":
            if args:
                self.search_files(args[0])
            else:
                self.log("Usage: /search <pattern>", "error")
        elif cmd == "/edit":
            if args:
                self.edit_file(args[0])
            else:
                self.log("Usage: /edit <filepath>", "error")
        elif cmd == "/history":
            self.show_history()
        elif cmd == "/undo":
            self.undo_action()
        elif cmd == "/redo":
            self.redo_action()
        elif cmd == "/logs":
            self.show_logs()
        elif cmd == "/whoami":
            self.whoami()
        elif cmd == "/date":
            self.show_date()
        elif cmd == "/uptime":
            self.show_uptime()
        elif cmd == "/memory":
            self.show_memory()
        elif cmd == "/disk":
            self.show_disk()
        elif cmd == "/provider":
            if args:
                self.provider = args[0]
                self.log(f"Provider switched to {self.provider}")
            else:
                self.log(f"Current provider: {self.provider}")
        elif cmd == "/model":
            if args:
                self.model = args[0]
                self.log(f"Model switched to {self.model}")
            else:
                self.log(f"Current model: {self.model}")
        elif cmd == "/clone-website" or cmd == "/clone":
            self.handle_clone_website()
        elif cmd == "/read":
            if args:
                self.read_file(args[0])
            else:
                self.log("Usage: /read [filepath]", "error")
        elif cmd == "/write":
            if args: self.write_file(args[0])
            else: self.log("Usage: /write [filepath]", "error")
        elif cmd == "/clear":
            content = load_prompt_content(self.prompt_file)
            self.history = [{"role": "system", "content": content}]
            os.system('cls' if os.name == 'nt' else 'clear')
            print_formatted_text(HTML(f"<banner>{BANNER}</banner>"))
        elif cmd in ["/exit", "/quit"]:
            self.log("Terminating Onyx session. Goodbye.", "system")
            sys.exit(0)
        else:
            self.log(f"Unknown command: {cmd}", "error")

    def show_help(self):
        help_text = """
Slash Commands:
  /help               - Show this documentation
  /config             - Interactively configure Onyx Settings
  /init               - Initialize workspace with default files
  /version            - Show Onyx Code version
  /stats              - Show system statistics
  /list               - List files in current or specified directory
  /tree               - Show directory tree structure
  /search             - Search for patterns in files
  /edit               - Open file in editor (or create if not exists)
  /history            - Show command history
  /undo               - Undo last action
  /redo               - Redo undone action
  /logs               - Show recent system logs
  /whoami             - Show who is running Onyx
  /date               - Show current date and time
  /uptime             - Show system uptime
  /memory             - Show memory usage
  /disk               - Show disk space usage
  /provider [name]    - Switch LLM provider
  /model [name]       - Switch active model
  /clone-website      - Clone a website via Chrome MCP
  /read [path]        - Ingest file into conversation context
  /write [path]       - Save last response (or extracted code) to file
  /clear              - Clear conversation history and screen
  /exit               - Quit Onyx Code

Web Clone Skill:
  /clone-website      - Run the clone-website skill to clone a website
  Usage: /clone-website <url> [options]
    - url: Target website to clone (required, e.g., "https://example.com")
    - pages: Which pages to replicate (default: ["home"])
    - fidelity: "pixel-perfect" | "high-fidelity" | "structural" (default: "pixel-perfect")
    - scope: "all" | "core-only" (default: "all")
    - customization: Modifications after clone (optional)

  Example:
    /clone-website https://example.com --pages=["home","about"] --fidelity=high-fidelity

  The skill runs a multi-phase pipeline:\n
    1. **Reconnaissance**: Inspect the target site via Chrome MCP to extract\n       design tokens and assets (colors, fonts, spacing, images, fonts).\n\n    2. **Foundation**: Create isolated git worktree and scaffolding files:\n       - package.json\n       - tsconfig.json\n       - tailwind.config.js\n       - postcss.config.js\n       - global.css\n\n    3. **Component Specs**: Analyze and write component specs for every section:\n       - Header/Nav Bar\n       - Hero Section\n       - Features Grid\n       - Testimonials\n       - Footer\n       - ... and more\n\n    4. **Parallel Build**: Dispatch parallel builder agents to reconstruct sections.\n\n    5. **Assembly & QA**: Merge worktrees, validate, optimize, and ensure\n       pixel-perfect fidelity.\n
  Configuration:\n    Edit **TARGET.md** before running for fine-grained control over:\n    - Pages: which pages to replicate (default: home page)
    - Fidelity: pixel-perfect, high-fidelity, or structural
    - Scope: what's in/out of scope
    - Customization plans: modifications to apply after the base clone
"""
        print(help_text)

    def handle_clone_website(self):
        """Handle the /clone-website command."""
        parts = self.session.prompt(HTML("onyx@code:~/clone> ")).strip()
        if not parts:
            self.log("No input provided. Use: /clone-website <url>", "error")
            return

        # Parse input
        args = parts.split()
        url = args[0] if len(args) > 0 else None
        options = {}

        # Parse optional arguments
        i = 1
        while i < len(args):
            arg = args[i].lower()
            if arg.startswith("--pages="):
                try:
                    pages_str = arg.split("=")[1]
                    pages = [p.strip("\"'\" ") for p in pages_str.split(",")]
                    options["pages"] = pages
                except (IndexError, ValueError):
                    self.log(f"Invalid --pages format: {arg}", "error")
            elif arg == "--fidelity":
                if i + 1 < len(args):
                    options["fidelity"] = args[i + 1]
                    i += 1
            elif arg == "--scope":
                if i + 1 < len(args):
                    options["scope"] = args[i + 1]
                    i += 1
            elif arg == "--customization":
                if i + 1 < len(args):
                    options["customization"] = args[i + 1]
                    i += 1
            i += 1

        if not url:
            self.log("No URL provided. Use: /clone-website <url>", "error")
            return

        # Validate URL
        if not (url.startswith("http://") or url.startswith("https://")):
            self.log(f"Invalid URL format: {url}", "error")
            return

        # Create a WebCloneSkill instance and run the pipeline
        clone_skill = WebCloneSkill()
        result = clone_skill.run_clone_pipeline(url, options)
        self.log("Clone pipeline completed successfully.", "success")

    def init_workspace(self):
        """Initialize workspace with default files."""
        import json
        workspace = "workspace"
        if not os.path.exists(workspace):
            os.makedirs(workspace, exist_ok=True)
        # Create default files
        defaults = {
            "README.md": "# Onyx Workspace\n\nThis is the default workspace for Onyx Code.\n",
            "config.json": "{}",
            "notes.txt": "Welcome to Onyx Code!\n\nThis workspace is initialized by default.\n",
            "tasks.md": "## Tasks\n\n- [ ] Add your tasks here\n- [ ] Track progress\n",
            "debug.py": "#!/usr/bin/env python3\n\n# Debug template\nprint('Debug template ready')\n"
        }
        for filename, content in defaults.items():
            filepath = os.path.join(workspace, filename)
            if not os.path.exists(filepath):
                with open(filepath, 'w') as f:
                    f.write(content)
                self.log(f"Created: {filename}", "success")
        self.log("Workspace initialized with default files.", "success")

    def show_version(self):
        """Show Onyx Code version."""
        version = "1.1.0"
        self.log(f"Onyx Code v{version} - AGENTIC AI CORE", "success")
        self.log(f"Python {sys.version.split()[0]}", "system")

    def show_stats(self):
        """Show system statistics."""
        import platform
        import socket
        import time

        self.log("\n--- System Statistics ---", "system")
        self.log(f"OS: {platform.system()} {platform.release()}", "system")
        self.log(f"Hostname: {socket.gethostname()}", "system")
        self.log(f"Platform: {platform.platform()}", "system")

        # CPU info
        try:
            import psutil
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()._asdict() if hasattr(psutil.cpu_freq(), '_asdict') else 'N/A'
            self.log(f"CPU Cores: {cpu_count}", "system")
            self.log(f"Memory Total: {psutil.virtual_memory().total / 1e9:.2f} GB", "system")
        except ImportError:
            self.log("psutil not installed, showing basic info", "system")

        # Python version
        self.log(f"Python: {sys.version}", "system")
        self.log(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "system")

    def list_path(self, path="."):
        """List files in a directory."""
        try:
            items = os.listdir(path)
            if os.path.isfile(path):
                if os.path.getsize(path) < 1024:
                    size = os.path.getsize(path)
                else:
                    size = f"{os.path.getsize(path) / 1024:.2f} KB"
                self.log(f"File: {path} ({size})", "system")
            else:
                self.log(f"Contents of '{path}':", "system")
                for item in sorted(items):
                    item_path = os.path.join(path, item)
                    if os.path.isdir(item_path):
                        self.log(f"  [DIR]  {item}/", "system")
                    else:
                        if os.path.getsize(item_path) < 1024:
                            size = os.path.getsize(item_path)
                        else:
                            size = f"{os.path.getsize(item_path) / 1024:.2f} KB"
                        self.log(f"  [FILE] {item} ({size})", "system")
        except Exception as e:
            self.log(f"Error listing directory: {str(e)}", "error")

    def show_tree(self, path=".", depth=0, max_depth=3):
        """Show directory tree structure."""
        try:
            prefix = "" if depth == 0 else "|" * depth + "--"
            items = sorted(os.listdir(path))
            self.log(f"{prefix} {path}:", "system")
            for i, item in enumerate(items):
                item_path = os.path.join(path, item)
                is_last = "" if i == len(items) - 1 else "\u250c" if depth < max_depth else "\u2500"
                connector = "\u250c\u2500\u2500\u2500" if depth < max_depth else "\u2500" * 5
                if os.path.isdir(item_path):
                    self.log(f"{is_last} \u2502  {item}/", "system")
                    if depth < max_depth:
                        self.show_tree(item_path, depth + 1, max_depth)
                else:
                    self.log(f"{is_last} \u2514  {item}", "system")
        except Exception as e:
            self.log(f"Error showing tree: {str(e)}", "error")

    def search_files(self, pattern, path="."):
        """Search for patterns in files."""
        import re
        matches = []
        try:
            for root, dirs, files in os.walk(path):
                for file in files:
                    if pattern.lower() in file.lower():
                        filepath = os.path.join(root, file)
                        try:
                            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                if pattern.lower() in content.lower():
                                    matches.append((filepath, pattern))
                        except:
                            pass
            if matches:
                self.log(f"\nFound {len(matches)} match(es):", "success")
                for filepath, pat in matches[:10]:  # Limit to 10
                    relpath = os.path.relpath(filepath, path)
                    self.log(f"  {relpath}: contains '{pat}'", "system")
            else:
                self.log(f"No matches found for '{pattern}'", "system")
        except Exception as e:
            self.log(f"Search error: {str(e)}", "error")

    def edit_file(self, filepath):
        """Open file in editor (or create if not exists)."""
        editor = os.environ.get('EDITOR', 'nano')
        if not os.path.exists(filepath):
            self.log(f"Creating new file: {filepath}", "system")
            with open(filepath, 'w') as f:
                f.write("# New file\n")
            self.log(f"Created empty file. Open with: {editor} {filepath}", "success")
        else:
            self.log(f"Opening: {editor} {filepath}", "system")
            self.execute_shell(f"{editor} {filepath}")

    def show_history(self):
        """Show command history."""
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r') as f:
                    history = f.readlines()
                self.log(f"\n--- Recent History ({len(history)} entries) ---", "system")
                for line in history[-20:]:  # Last 20 entries
                    self.log(f"  {line.strip()}", "system")
            except Exception as e:
                self.log(f"History read error: {str(e)}", "error")
        else:
            self.log("No history file found.", "system")

    def undo_action(self):
        """Undo last action (placeholder)."""
        self.log("Undo is not yet implemented. Use /clear to reset session.", "system")

    def redo_action(self):
        """Redo undone action (placeholder)."""
        self.log("Redo is not yet implemented. Use /config to reload.", "system")

    def show_logs(self):
        """Show recent system logs."""
        # These would typically be stored in a log file
        # For now, show some default info
        self.log("\n--- Recent System Logs ---", "system")
        self.log(f"Onyx Code started at: {datetime.now()}", "system")
        self.log(f"Provider: {self.provider}", "system")
        self.log(f"Model: {self.model}", "system")
        self.log(f"Prompt: {self.prompt_file}", "system")
        self.log("--- End Logs ---", "system")

    def whoami(self):
        """Show who is running Onyx."""
        try:
            import pwd
            username = pwd.getpwuid(os.getuid()).pw_name
            self.log(f"Running as: {username}", "system")
            self.log(f"Home directory: {os.path.expanduser('~')}", "system")
        except:
            self.log(f"Username: {os.environ.get('USER', 'unknown')}", "system")

    def show_date(self):
        """Show current date and time."""
        now = datetime.now()
        self.log(f"\nCurrent Date/Time: {now.strftime('%A, %B %d, %Y %I:%M:%S %p')}", "system")
        self.log(f"Unix Timestamp: {int(now.timestamp())}", "system")

    def show_uptime(self):
        """Show system uptime."""
        try:
            import platform
            if platform.system() == 'Linux':
                with open('/proc/uptime', 'r') as f:
                    uptime_seconds = float(f.read().split()[0])
                    uptime_days = uptime_seconds / 86400
                    self.log(f"\nSystem Uptime: {uptime_days:.2f} days ({uptime_seconds:.0f} seconds)", "system")
            else:
                self.log("Uptime not available on this platform.", "system")
        except:
            self.log("Unable to read uptime.", "system")

    def show_memory(self):
        """Show memory usage."""
        try:
            import psutil
            memory = psutil.virtual_memory()
            percent = memory.percent
            total_gb = memory.total / 1e9
            used_gb = memory.used / 1e9
            self.log(f"\nMemory Usage: {percent:.1f}% ({used_gb:.2f} GB / {total_gb:.2f} GB)", "system")
            self.log(f"  Free: {(memory.available / 1e9):.2f} GB", "system")
        except ImportError:
            self.log("psutil not installed. Use: pip install psutil", "system")
        except Exception as e:
            self.log(f"Memory error: {str(e)}", "error")

    def show_disk(self):
        """Show disk space usage."""
        try:
            import psutil
            partitions = psutil.disk_partitions()
            self.log("\n--- Disk Partitions ---", "system")
            for part in partitions:
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    total_gb = usage.total / 1e9
                    used_gb = usage.used / 1e9
                    free_gb = usage.free / 1e9
                    self.log(f"{part.mountpoint}: {usage.percent}% used ({used_gb:.2f} GB / {total_gb:.2f} GB)", "system")
                except:
                    self.log(f"{part.mountpoint}: (unable to read usage)", "system")
        except ImportError:
            self.log("psutil not installed. Use: pip install psutil", "system")
        except Exception as e:
            self.log(f"Disk error: {str(e)}", "error")

    def read_file(self, filepath: str):
        try:
            if not os.path.exists(filepath):
                self.log(f"File not found: {filepath}", "error")
                return
            with open(filepath, 'r') as f:
                content = f.read()
                self.history.append({"role": "user", "content": f"Context from file '{filepath}':\n\n{content}"})
                self.log(f"Ingested {filepath} into context.")
        except Exception as e:
            self.log(f"Read error: {str(e)}", "error")

    def write_file(self, filepath: str, content: str = None):
        if content is None:
            if not self.history:
                self.log("No content to write.", "error")
                return
            last_resp = next((m["content"] for m in reversed(self.history) if m["role"] == "assistant"), None)
            if not last_resp:
                self.log("No assistant response found in history.", "error")
                return
            
            code_blocks = re.findall(r"```.*?\n(.*?)\n```", last_resp, re.DOTALL)
            content = code_blocks[0] if code_blocks else last_resp

        try:
            # Ensure workspace exists if target is in workspace/
            if filepath.startswith("workspace/"):
                os.makedirs("workspace", exist_ok=True)

            os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True) if os.path.dirname(filepath) else None
            with open(filepath, 'w') as f:
                f.write(content)
                self.log(f"SAVED: {filepath}", "success")
        except Exception as e:
            self.log(f"Write error: {str(e)}", "error")

    def execute_shell(self, command: str):
        self.log(f"ONYX REQUEST: Shell Execution", "system")
        print_formatted_text(HTML(f"Command: <ansigray>{command}</ansigray>"))
        # Check if running in interactive mode
        if not sys.stdin.isatty():
            # Non-interactive mode - auto-approve
            self.log("Running in non-interactive mode, auto-approving...", "system")
        else:
            confirm = self.session.prompt(HTML("<execution>Allow execution? (y/N): </execution>")).lower()
            if confirm != 'y':
                return "Command denied by user."

        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
            output = result.stdout + result.stderr
            self.log("Execution completed.", "success")
            return output
        except subprocess.TimeoutExpired:
            return "Command timed out after 60 seconds."
        except Exception as e:
            error_msg = f"Execution error: {str(e)}"
            self.log(error_msg, "error")
            return error_msg

    def fallback_search(self, query: str):
        self.log(f"Searching web for: {query}...", "system")
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
                context = "\n".join([f"- {r['title']}: {r['body']}" for r in results])
                return context
        except Exception as e:
            return f"Search failed: {str(e)}"

    def parse_ai_actions(self, text: str):
        # 1. Look for legacy tags
        write_matches = re.finditer(r"\[WRITE:(.*?)\]", text)
        for match in write_matches:
            path = match.group(1)
            after_text = text[match.end():]
            code_blocks = re.findall(r"```.*?\n(.*?)\n```", after_text, re.DOTALL)
            if code_blocks:
                self.write_file(path, code_blocks[0])

        shell_matches = re.findall(r"\[SHELL:(.*?)\]", text)
        for cmd in shell_matches:
            output = self.execute_shell(cmd)
            self.history.append({"role": "user", "content": f"[SYSTEM CONTEXT: Shell Output for '{cmd}']\n{output}"})
            self.log("Feeding output back to Onyx...", "system")
            # We don't trigger chat here, we'll let the caller handle continuity if needed
            # or just rely on the next message
            # For legacy actions, we might still want to trigger if it's the main response
            # but legacy is being phased out in favor of tools

        # Handle run_command legacy tag
        run_command_matches = re.finditer(r"\[run_command:(.*?)\]", text)
        for match in run_command_matches:
            command_str = match.group(1)
            # The command is everything between the colon and the next ]
            if command_str.startswith('{'):
                try:
                    command = json.loads(command_str)
                    if 'command' in command:
                        self.log(f"Legacy run_command tag: {command['command']}", "system")
                        self.execute_shell(command['command'])
                        self.history.append({"role": "user", "content": f"[SYSTEM CONTEXT: Legacy run_command output]\n"})
                        self.log("run_command executed successfully.", "success")
                except json.JSONDecodeError as e:
                    self.log(f"Failed to parse run_command JSON: {str(e)}", "error")
                    # Show the problematic string for debugging
                    self.log(f"Problematic JSON: {repr(command_str)}", "error")
            else:
                # Handle raw command (for backwards compatibility)
                self.log(f"Legacy run_command (raw): {command_str}", "system")
                self.execute_shell(command_str)

        tool_matches = re.finditer(r"\[USE_TOOL:(.*?)\{(.*?)\}\]", text)
        for match in tool_matches:
            tool_name = match.group(1).strip()
            tool_args_str = "{" + match.group(2) + "}"
            try:
                tool_args = json.loads(tool_args_str)
                self.log(f"MCP REQUEST: {tool_name}", "system")
                if self.mcp_client:
                    result = anyio.run(self.mcp_client.call_tool, tool_name, tool_args)
                    self.history.append({"role": "user", "content": f"[SYSTEM CONTEXT: MCP Tool '{tool_name}' Output]\n{str(result)}"})
                    self.log(f"Tool {tool_name} executed successfully.", "success")
                else:
                    self.log("MCP Client not configured.", "error")
            except json.JSONDecodeError as e:
                self.log(f"Failed to parse USE_TOOL JSON for {tool_name}: {str(e)}", "error")
                self.log(f"Problematic JSON: {repr(tool_args_str)}", "error")
            except Exception as e:
                self.log(f"Tool execution failed: {str(e)}", "error")

        # 2. Look for JSON Tool Calls (fallback for models that don't use native tool calling)
        json_blocks = re.findall(r"```(?:json)?\s*\n(.*?)\n\s*```", text, re.DOTALL)
        
        # If no blocks found, check if the entire text (or a significant portion) is JSON
        if not json_blocks:
            # Simple heuristic: if it looks like a JSON object
            stripped = text.strip()
            if (stripped.startswith("{") and stripped.endswith("}")):
                json_blocks.append(stripped)
            elif "{" in text and "}" in text:
                # Try to find something that looks like a tool call inside
                maybe_json = re.findall(r"(\{.*?\})", text, re.DOTALL)
                for item in maybe_json:
                    if '"name":' in item and ('"arguments":' in item or '"function":' in item):
                        json_blocks.append(item)

        any_tool_executed = False
        for block in json_blocks:
            try:
                data = json.loads(block.strip())
                name = data.get("name")
                args = data.get("arguments")
                
                if not name and "function" in data:
                    name = data["function"].get("name")
                    args = data["function"].get("arguments")
                
                if name and args is not None:
                    self.log(f"JSON TOOL DETECTED: {name}", "system")
                    self.execute_tool_by_name(name, args, None)
                    any_tool_executed = True
            except json.JSONDecodeError:
                continue
        return any_tool_executed

    def execute_tool_by_name(self, func_name: str, args: dict, tool_call_id: Optional[str] = None):
        self.log(f"TOOL EXECUTION: {func_name}", "system")

        result = ""
        if func_name == "write_file":
            try:
                self.write_file(args.get("path"), args.get("content"))
                result = f"File {args.get('path')} written successfully."
            except Exception as e:
                result = f"Error writing file: {str(e)}"
        elif func_name == "run_command":
            result = self.execute_shell(args.get("command"))
        elif func_name == "read_file":
            try:
                with open(args.get("path"), 'r', encoding='utf-8', errors='ignore') as f:
                    result = f.read()
            except Exception as e:
                result = f"Error reading file: {str(e)}"
        elif func_name == "list_dir":
            try:
                path = args.get("path", ".")
                files = os.listdir(path)
                result = "\n".join(files)
            except Exception as e:
                result = f"Error listing directory: {str(e)}"
        elif func_name is None or func_name == "":
             result = "Error: Missing tool name."
        else:
             result = f"Error: Tool '{func_name}' not recognized."

        # Append tool result to history
        if tool_call_id:
            tool_entry = {
                "role": "tool",
                "name": func_name,
                "tool_call_id": tool_call_id,
                "content": str(result)
            }
        else:
            tool_entry = {
                "role": "user",
                "content": f"[SYSTEM TOOL OUTPUT: {func_name}]\n{result}"
            }
        self.history.append(tool_entry)
        return result

    def chat(self, user_input: str = None, auto_trigger: bool = False, depth: int = 0):
        if depth > 5:
            self.log("Maximum tool call depth reached.", "error")
            return

        if user_input:
            self.history.append({"role": "user", "content": user_input})
        
        try:
            api_base = self.endpoint if self.endpoint else None
            
            if self.provider == "local":
                model_string = f"openai/{self.model}"
                api_base = api_base or "http://localhost:8080/v1"
            elif self.provider == "openai":
                model_string = self.model
            elif self.provider == "ollama":
                model_string = f"ollama/{self.model}"
                if api_base:
                    # Clean up Ollama endpoint to base URL
                    api_base = api_base.rstrip('/')
                    for suffix in ['/api/chat', '/api/generate', '/v1']:
                        if api_base.endswith(suffix):
                            api_base = api_base[:-len(suffix)]
            else:
                model_string = f"{self.provider}/{self.model}"
            
            if user_input and any(k in user_input.lower() for k in ["search", "who is", "latest", "internet"]):
                search_data = self.fallback_search(user_input)
                self.history.append({"role": "user", "content": f"[SYSTEM CONTEXT: Web Search Results]\n{search_data}"})

            if not auto_trigger:
                think_states = ["Cooking...", "Analyzing system architecture...", "Optimizing payload...", "Finishing the job...", "Structuring response..."]
                self.log(random.choice(think_states), "system")

            start_time = time.time()
            
            # Tools to use
            tools = get_internal_tools()
            
            # Detect if model supports tools via litellm (gemini, openai, anthropic, ollama-v1)
            # Some older ollama or custom local endpoints might not.
            # We'll pass them and let litellm handle it.
            
            response = litellm.completion(
                model=model_string,
                messages=self.history,
                temperature=0.7,
                api_base=api_base,
                api_key=self.api_key if self.api_key else "sk-onyx-dummy-key",
                tools=tools,
                stream=True
            )
            
            if not auto_trigger:
                print(f"\nONYX ({self.provider}): ", end="")
            
            resp_text = ""
            reasoning_text = ""
            tool_calls = []
            
            # Tracking if we are currently printing reasoning to manage line breaks/styles
            is_reasoning = False
            
            try:
                for chunk in response:
                    delta = chunk.choices[0].delta
                    
                    # Check for tool calls
                    if hasattr(delta, 'tool_calls') and delta.tool_calls:
                        for tc in delta.tool_calls:
                            # Find existing tool call in the list or create new one
                            existing_tc = next((x for x in tool_calls if x['index'] == tc.index), None)
                            if not existing_tc:
                                tool_calls.append({
                                    'index': tc.index,
                                    'id': tc.id,
                                    'type': 'function',
                                    'function': {
                                        'name': tc.function.name or "",
                                        'arguments': tc.function.arguments or ""
                                    }
                                })
                            else:
                                if tc.function.name:
                                    existing_tc['function']['name'] += tc.function.name
                                if tc.function.arguments:
                                    existing_tc['function']['arguments'] += tc.function.arguments
                        continue

                    # Try to get reasoning content (supported by some models/litellm)
                    reasoning = getattr(delta, 'reasoning_content', None)
                    if reasoning:
                        if not is_reasoning:
                            print("\n[THOUGHT] ", end="", flush=True)
                            is_reasoning = True
                        print_formatted_text(FormattedText([('class:thought', reasoning)]), end="", style=STYLE, flush=True)
                        reasoning_text += reasoning
                        continue
                    
                    content = delta.content or ""
                    if content:
                        if is_reasoning:
                            print("\n") # New line after finishing reasoning
                            is_reasoning = False
                        print(content, end="", flush=True)
                        resp_text += content
            except json.JSONDecodeError as e:
                print() # Ensure newline
                self.log(f"JSON decode error: {str(e)}", "error")
                self.log(f"Error location: line {e.lineno}, column {e.colno}", "error")
                # We can still proceed with what we got so far
            except Exception as e:
                print() # Ensure newline
                self.log(f"Unexpected error: {type(e).__name__}: {str(e)}", "error")
                # We can still proceed with what we got so far
            except Exception as stream_err:
                print() # Ensure newline
                self.log(f"Stream interrupted: {str(stream_err)}", "error")
                # We can still proceed with what we got so far
            
            if not auto_trigger:
                print()
            
            duration = time.time() - start_time
            
            # Record assistant msg
            assistant_msg = {"role": "assistant"}
            if resp_text:
                assistant_msg["content"] = resp_text
                if reasoning_text:
                    assistant_msg["content"] = f"<thought>{reasoning_text}</thought>\n{resp_text}"
            
            if tool_calls:
                # Clean up tool calls for litellm history (removing 'index')
                final_tool_calls = []
                for tc in tool_calls:
                    final_tool_calls.append({
                        "id": tc['id'],
                        "type": "function",
                        "function": tc['function']
                    })
                assistant_msg["tool_calls"] = final_tool_calls
                if not assistant_msg.get("content"):
                    assistant_msg["content"] = None # Some APIs require content to be present or null

            self.history.append(assistant_msg)
            
            if not auto_trigger:
                tokens = (len(resp_text.split()) + len(reasoning_text.split())) * 1.3 
                tps = tokens / duration if duration > 0 else 0
                print(f"[METRICS] ~{int(tokens)} tokens | {tps:.1f} tokens/s | {duration:.2f}s\n")
            
            # Handle tool calls
            any_tool_invoked = False
            if tool_calls:
                any_tool_invoked = True
                for tc in tool_calls:
                    func_name = tc['function']['name']
                    try:
                        args = json.loads(tc['function']['arguments'])
                    except json.JSONDecodeError as e:
                        self.log(f"Failed to parse tool args for {func_name}: {str(e)}", "error")
                        self.log(f"Arguments JSON: {repr(tc['function']['arguments'])}", "error")
                        self.log(f"Full tool call: {tc}", "error")
                        args = {"raw_args": tc['function']['arguments']}

                    self.execute_tool_by_name(func_name, args, tc['id'])

            # Also check for actions in the text if any
            if resp_text:
                if self.parse_ai_actions(resp_text):
                    any_tool_invoked = True
            
            if any_tool_invoked:
                # One recursive call to process all findings
                self.chat(auto_trigger=True, depth=depth + 1)
            
        except Exception as e:
            self.log(f"AI Error: {str(e)}", "error")


    def run(self):
        print_formatted_text(HTML(f"<banner>{BANNER}</banner>"), style=STYLE)

        # Check if configuration is missing
        if not self.config:
            self.log("Configuration needed! Use 'python onyx_code.py --config' to first configure.", "error")

        self.log(f"Initialized with {self.provider.upper()} ({self.model}) | File: {self.prompt_file}", "system")

        # Capture the last user message before session ends
        last_user_input = ""

        while True:
            try:
                user_msg = self.session.prompt("onyx@code:~$ ")
                if not user_msg.strip(): continue
                last_user_input = user_msg  # Track for session saving
                if user_msg.startswith("/"):
                    self.handle_command(user_msg)
                else:
                    self.chat(user_msg)
            except KeyboardInterrupt:
                continue
            except EOFError:
                break

        # Save session on exit
        try:
            session_id = f"{int(time.time())}"
            session_data = {
                "provider": self.provider,
                "model": self.model,
                "api_key": self.api_key,
                "endpoint": self.endpoint,
                "prompt_file": self.prompt_file,
                "mcp_command": self.mcp_command,
                "history": self.history,
                "current_user": os.environ.get("USER", ""),
                "last_command": last_user_input,
                "timestamp": str(int(time.time())),
                "last_active": str(int(time.time())),
            }
            save_session(session_id, session_data)
            self.log(f"Session saved as: {session_id}", "system")
        except Exception as e:
            self.log(f"Error saving session: {str(e)}", "error")

def save_session(session_id, session_data):
    """Save a session with its data."""
    try:
        import json
        import os
        session_dir = os.path.expanduser("~/.onyx_sessions")
        os.makedirs(session_dir, exist_ok=True)
        session_path = os.path.join(session_dir, session_id + ".json")

        # Convert session_data to JSON-serializable format
        serializable_data = {
            "provider": session_data.get("provider", ""),
            "model": session_data.get("model", ""),
            "api_key": session_data.get("api_key", ""),
            "endpoint": session_data.get("endpoint", ""),
            "prompt_file": session_data.get("prompt_file", ""),
            "mcp_command": session_data.get("mcp_command", ""),
            "history": session_data.get("history", []),
            "current_user": session_data.get("current_user", ""),
            "last_command": session_data.get("last_command", ""),
            "timestamp": session_data.get("timestamp", str(int(time.time()))),
            "last_active": session_data.get("last_active", str(int(time.time()))),
        }

        with open(session_path, 'w') as f:
            json.dump(serializable_data, f, indent=2)

        return True
    except Exception as e:
        print(f"Error saving session: {str(e)}")
        return False


def resume_session(session_id):
    """Load and resume a saved session."""
    try:
        import json
        import os

        session_dir = os.path.expanduser("~/.onyx_sessions")
        session_path = os.path.join(session_dir, session_id + ".json")

        if not os.path.exists(session_path):
            print(f"Session not found: {session_id}")
            print(f"Available sessions:")
            list_sessions()
            return

        with open(session_path, 'r') as f:
            session_data = json.load(f)

        # Print session info
        timestamp = session_data.get("timestamp", "Unknown")
        last_active = session_data.get("last_active", timestamp)
        last_command = session_data.get("last_command", "None")
        print(f"\n--- Resuming Session: {session_id} ---")
        print(f"Saved at: {timestamp}")
        print(f"Last active: {last_active}")
        print(f"Last command: {last_command}")
        print(f"Provider: {session_data.get('provider', 'N/A')}")
        print(f"Model: {session_data.get('model', 'N/A')}")
        print(f"\nLoading {len(session_data.get('history', []))} messages into context...\n")

        # Create a new OnyxCode instance with the saved data
        app = OnyxCode()
        app.provider = session_data.get("provider", "") or "ollama"
        app.model = session_data.get("model", "") or "minimax-m2.5:cloud"
        app.api_key = session_data.get("api_key", "")
        app.endpoint = session_data.get("endpoint", "")
        app.prompt_file = session_data.get("prompt_file", "")
        app.mcp_command = session_data.get("mcp_command", "")
        app.history = session_data.get("history", [])
        app.last_command = session_data.get("last_command", "")

        if app.history:
            app.log(f"Loaded {len(app.history)} messages from session.", "system")
        else:
            app.log("No history found in session.", "system")

        # Continue with the session
        app.run()

    except FileNotFoundError:
        print(f"Session file not found: {session_id}")
        print("Available sessions:")
        list_sessions()
    except json.JSONDecodeError:
        print(f"Error reading session file: {session_id}")
    except Exception as e:
        print(f"Error resuming session: {str(e)}")


def list_sessions():
    """List all saved sessions."""
    session_dir = os.path.expanduser("~/.onyx_sessions")
    sessions = []

    try:
        if os.path.exists(session_dir):
            for filename in os.listdir(session_dir):
                if filename.endswith(".json"):
                    sessions.append(filename)
    except Exception as e:
        print(f"Error listing sessions: {str(e)}")

    if sessions:
        print(f"\nAvailable sessions ({len(sessions)}):")
        for session_id in sorted(sessions):
            session_path = os.path.join(session_dir, session_id)
            try:
                with open(session_path, 'r') as f:
                    data = json.load(f)
                timestamp = data.get("timestamp", "Unknown")
                last_active = data.get("last_active", timestamp)
                print(f"  - {session_id}")
                print(f"    Saved: {timestamp}")
                print(f"    Last active: {last_active}")
            except Exception as e:
                print(f"  - {session_id} (Error reading: {str(e)})")
    else:
        print("No saved sessions found.")
        print("Sessions are automatically saved when you exit Onyx Code.")


def main():
    parser = argparse.ArgumentParser(description="Onyx Code - AI CLI Tool")
    parser.add_argument("--config", action="store_true", help="Launch interactive configuration")
    parser.add_argument("--resume", nargs="?", help="Resume a saved session")
    parser.add_argument("--version", action="version", version="1.1.0")
    args = parser.parse_args()

    if not args.config and not args.resume:
        # Default: run interactive session
        app = OnyxCode()
        app.run()

    elif args.config:
        app = OnyxCode()
        app.configure_interactively()

    elif args.resume:
        try:
            session_id = args.resume
            resume_session(session_id)
        except Exception as e:
            print(f"Error: {str(e)}")


def save_session(session_id, session_data):
    """Save a session with its data."""
    try:
        import json
        import os
        session_dir = "~/.onyx_sessions"
        os.makedirs(session_dir, exist_ok=True)
        session_path = os.path.join(session_dir, session_id + ".json")

        # Convert session_data to JSON-serializable format
        serializable_data = {
            "provider": session_data.get("provider", ""),
            "model": session_data.get("model", ""),
            "api_key": session_data.get("api_key", ""),
            "endpoint": session_data.get("endpoint", ""),
            "prompt_file": session_data.get("prompt_file", ""),
            "mcp_command": session_data.get("mcp_command", ""),
            "history": session_data.get("history", []),
            "current_user": session_data.get("current_user", ""),
            "last_command": session_data.get("last_command", ""),
            "timestamp": session_data.get("timestamp", str(int(time.time()))),
            "last_active": session_data.get("last_active", str(int(time.time()))),
        }

        with open(session_path, 'w') as f:
            json.dump(serializable_data, f, indent=2)

        return True
    except Exception as e:
        print(f"Error saving session: {str(e)}")
        return False


def resume_session(session_id):
    """Load and resume a saved session."""
    try:
        import json
        import os

        session_dir = os.path.expanduser("~/.onyx_sessions")
        session_path = os.path.join(session_dir, session_id + ".json")

        if not os.path.exists(session_path):
            print(f"Session not found: {session_id}")
            print(f"Available sessions:")
            list_sessions()
            return

        with open(session_path, 'r') as f:
            session_data = json.load(f)

        # Print session info
        timestamp = session_data.get("timestamp", "Unknown")
        last_active = session_data.get("last_active", timestamp)
        last_command = session_data.get("last_command", "None")
        print(f"\n--- Resuming Session: {session_id} ---")
        print(f"Saved at: {timestamp}")
        print(f"Last active: {last_active}")
        print(f"Last command: {last_command}")
        print(f"Provider: {session_data.get('provider', 'N/A')}")
        print(f"Model: {session_data.get('model', 'N/A')}")
        print(f"\nLoading {len(session_data.get('history', []))} messages into context...\n")

        # Create a new OnyxCode instance with the saved data
        app = OnyxCode()
        app.provider = session_data.get("provider", "") or "ollama"
        app.model = session_data.get("model", "") or "minimax-m2.5:cloud"
        app.api_key = session_data.get("api_key", "")
        app.endpoint = session_data.get("endpoint", "")
        app.prompt_file = session_data.get("prompt_file", "")
        app.mcp_command = session_data.get("mcp_command", "")
        app.history = session_data.get("history", [])
        app.last_command = session_data.get("last_command", "")

        if app.history:
            app.log(f"Loaded {len(app.history)} messages from session.", "system")
        else:
            app.log("No history found in session.", "system")

        # Continue with the session
        app.run()

    except FileNotFoundError:
        print(f"Session file not found: {session_id}")
        print("Available sessions:")
        list_sessions()
    except json.JSONDecodeError:
        print(f"Error reading session file: {session_id}")
    except Exception as e:
        print(f"Error resuming session: {str(e)}")


def list_sessions():
    """List all saved sessions."""
    session_dir = os.path.expanduser("~/.onyx_sessions")
    sessions = []

    try:
        if os.path.exists(session_dir):
            for filename in os.listdir(session_dir):
                if filename.endswith(".json"):
                    sessions.append(filename)
    except Exception as e:
        print(f"Error listing sessions: {str(e)}")

    if sessions:
        print(f"\nAvailable sessions ({len(sessions)}):")
        for session_id in sorted(sessions):
            session_path = os.path.join(session_dir, session_id)
            try:
                with open(session_path, 'r') as f:
                    data = json.load(f)
                timestamp = data.get("timestamp", "Unknown")
                last_active = data.get("last_active", timestamp)
                print(f"  - {session_id}")
                print(f"    Saved: {timestamp}")
                print(f"    Last active: {last_active}")
            except Exception as e:
                print(f"  - {session_id} (Error reading: {str(e)})")
    else:
        print("No saved sessions found.")
        print("Sessions are automatically saved when you exit Onyx Code.")


if __name__ == "__main__":
    main()
