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

def get_internal_tools():
    return [
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
        elif cmd == "/read":
            if args: self.read_file(args[0])
            else: self.log("Usage: /read [filepath]", "error")
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
  /provider [name]    - Switch LLM provider
  /model [name]       - Switch active model
  /read [path]        - Ingest file into conversation context
  /write [path]       - Save last response (or extracted code) to file
  /clear              - Clear conversation history and screen
  /exit               - Quit Onyx Code

MCP Integration:
  - Configure via /config (MCP Server Command)
  - AI can call tools using [USE_TOOL:name{args}]
        """
        print(help_text)

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
        confirm = self.session.prompt(HTML("<execution>Allow execution? (y/N): </execution>")).lower()
        if confirm == 'y':
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                output = result.stdout + result.stderr
                self.log("Execution completed.", "success")
                return output
            except Exception as e:
                return f"Execution error: {str(e)}"
        return "Command denied by user."

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
            self.write_file(args.get("path"), args.get("content"))
            result = f"File {args.get('path')} written successfully."
        elif func_name == "run_command":
            result = self.execute_shell(args.get("command"))
        elif func_name == "read_file":
            try:
                with open(args.get("path"), 'r') as f:
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
                    except:
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
        
        while True:
            try:
                user_msg = self.session.prompt("onyx@code:~$ ")
                if not user_msg.strip(): continue
                if user_msg.startswith("/"):
                    self.handle_command(user_msg)
                else:
                    self.chat(user_msg)
            except KeyboardInterrupt:
                continue
            except EOFError:
                break

def main():
    parser = argparse.ArgumentParser(description="Onyx Code - AI CLI Tool")
    parser.add_argument("--config", action="store_true", help="Launch interactive configuration")
    args = parser.parse_args()

    app = OnyxCode()
    if args.config:
        app.configure_interactively()
    app.run()

if __name__ == "__main__":
    main()
