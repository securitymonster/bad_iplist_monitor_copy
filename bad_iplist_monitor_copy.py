import os
import time
import hashlib
import configparser
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from paramiko import SSHClient, AutoAddPolicy
import logging
from datetime import datetime

# Load configurations from a file
config = configparser.ConfigParser()
config.read('config.ini')

REMOTE_SERVER = config['SCP']['RemoteServer']
REMOTE_PORT = int(config['SCP']['Port'])
DESTINATION_PATH = config['SCP']['DestinationPath']
SSH_KEY_PATH = config['SCP']['SSHKeyPath']
MONITOR_PATH = config['SCP']['MonitorPath']
LOG_FILE = config['SCP']['LogFile']

# Setup logging
logging.basicConfig(filename=LOG_FILE, level=logging.INFO)

def hash_file(filename):
    """Generate a SHA-256 hash of a file."""
    hasher = hashlib.sha256()
    with open(filename, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def scp_file(file_path, destination):
    """Securely copy a file to the remote server."""
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())
    client.connect(REMOTE_SERVER, port=REMOTE_PORT, key_filename=SSH_KEY_PATH)
    scp = SCPClient(client.get_transport())
    
    try:
        scp.put(file_path, destination)
        scp.close()
        return True
    except Exception as e:
        logging.error(f"Error in SCP transfer: {e}")
        return False
    finally:
        client.close()

class NewFileHandler(FileSystemEventHandler):
    """Handle new file creation events."""
    def on_created(self, event):
        if not event.is_directory:
            file_path = event.src_path
            file_hash = hash_file(file_path)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            success = scp_file(file_path, DESTINATION_PATH + '/' + os.path.basename(file_path))
            result = "Success" if success else "Failed"
            log_message = f"{timestamp}: File: {file_path}, Hash: {file_hash}, SCP: {result}"
            logging.info(log_message)

if __name__ == "__main__":
    event_handler = NewFileHandler()
    observer = Observer()
    observer.schedule(event_handler, path=MONITOR_PATH, recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
