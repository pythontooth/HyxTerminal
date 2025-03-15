from datetime import datetime
    
def timestamp_command(*args):
    print(f"Current timestamp: {datetime.now()}")
    
def setup(terminal):
    terminal.register_command("timestamp", timestamp_command, "Show current timestamp")
    return {"name": "Example Plugin", "version": "1.0"}