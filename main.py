"""
Hf-Coder: A Python Coding Agent with Web Search and File Management
Main entry point for the application
"""

import os
import sys
from agent import HfCoderAgent
from config import Config

# ASCII Art Banner
ASCII_BANNER = r"""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║    ██╗  ██╗███████╗       ██████╗ ███████╗██╗   ██╗███████╗██╗   ║
║    ██║  ██║██╔════╝      ██╔════╝ ██╔════╝██║   ██║██╔════╝██║   ║
║    ███████║█████╗        ██║  ███╗█████╗  ██║   ██║█████╗  ██║   ║
║    ██╔══██║██╔══╝        ██║   ██║██╔══╝  ██║   ██║██╔══╝  ╚═╝   ║
║    ██║  ██║███████╗      ╚██████╔╝███████╗╚██████╔╝███████╗██╗   ║
║    ╚═╝  ╚═╝╚══════╝       ╚═════╝ ╚══════╝ ╚═════╝ ╚══════╝╚═╝   ║
║                                                                   ║
║    Your AI-Powered Python Coding Assistant                       ║
║    🤖 Web Search • 📝 File Management • ⚙️ Smart Commands       ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
"""


def print_welcome():
    """Print welcome message and banner"""
    print(ASCII_BANNER)
    print("\n✨ Welcome to Hf-Coder!")
    print("📚 Type '/help' to see all available commands")
    print("🔍 Type '/search <query>' to search Wikipedia")
    print("📝 Type '/create <filename>' to create files")
    print("⚙️  Type '/config' to view/modify settings")
    print("❌ Type '/exit' to quit\n")


def main():
    """Main function to run the Hf-Coder agent"""
    # Create workspace directory if it doesn't exist
    workspace_dir = "./hf_coder_workspace"
    if not os.path.exists(workspace_dir):
        os.makedirs(workspace_dir)
        print(f"✅ Created workspace directory: {workspace_dir}\n")

    # Initialize agent
    try:
        print("🔄 Initializing Hf-Coder agent...")
        agent = HfCoderAgent(workspace_dir=workspace_dir)
        print("✅ Agent initialized successfully!\n")
    except Exception as e:
        print(f"❌ Error initializing agent: {e}")
        print("💡 Make sure you have installed all dependencies: pip install -r requirements.txt")
        sys.exit(1)

    # Print welcome message
    print_welcome()

    # Main conversation loop
    try:
        while True:
            try:
                user_input = input("👤 You: ").strip()

                if not user_input:
                    continue

                # Process user input
                response = agent.process_input(user_input)
                print(f"🤖 Agent: {response}\n")

                # Check if agent should exit
                if agent.should_exit:
                    print("👋 Goodbye! Thanks for using Hf-Coder!")
                    break

            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted by user")
                break
            except Exception as e:
                print(f"❌ Error processing input: {e}")
                continue

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
