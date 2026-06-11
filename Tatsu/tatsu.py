"""
Tatsu AI — Entry Point
========================
Main entry point for the Tatsu AI assistant.
Initializes all subsystems and starts the server.
"""

import sys
import webbrowser
import threading
import time

import config


def main():
    """Start Tatsu AI."""
    if sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except AttributeError:
            pass
    print(r"""
    ╔══════════════════════════════════════════════════╗
    ║                                                  ║
    ║          ████████╗ █████╗ ████████╗███████╗██╗   ║
    ║          ╚══██╔══╝██╔══██╗╚══██╔══╝██╔════╝██║   ║
    ║             ██║   ███████║   ██║   ███████╗██║   ║
    ║             ██║   ██╔══██║   ██║   ╚════██║██║   ║
    ║             ██║   ██║  ██║   ██║   ███████║███║  ║
    ║             ╚═╝   ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚══╝  ║
    ║                                                  ║
    ║         Local AI Assistant for Windows            ║
    ║                   v1.0.0                         ║
    ║                                                  ║
    ╚══════════════════════════════════════════════════╝
    """)

    print(f"  Model:   {config.OLLAMA_MODEL}")
    print(f"  Server:  http://{config.SERVER_HOST}:{config.SERVER_PORT}")
    print(f"  Data:    {config.DATA_DIR}")
    print()

    # Auto-open browser after a short delay
    if config.AUTO_OPEN_BROWSER:
        def open_browser():
            time.sleep(2)
            url = f"http://{config.SERVER_HOST}:{config.SERVER_PORT}"
            webbrowser.open(url)
            print(f"  🌐 Browser opened: {url}")
        threading.Thread(target=open_browser, daemon=True).start()

    # Start the server
    from api.server import run_server
    run_server()


if __name__ == "__main__":
    main()