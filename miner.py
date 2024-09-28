import requests
import hashlib
import time
import json
import threading
import sys
import os
import signal
import random
from datetime import datetime
from colorama import Fore, init

# Initialize colorama
init(autoreset=True)

MINER_ID = 'miner1'  # Unique miner ID
NODE_URL = 'http://192.168.0.103:5001/api'  # Node URL
RECEIPT_ADDRESS = 'TXVGuTWdPx1KuMo98oZDAb6SgZvUV8FS6r'  # Recipient address
NUM_THREADS = 1  # Number of mining threads
NONCE_RANGE = 1000000  # Total range of nonce to explore
stop_mining = False  # Control flag for stopping mining

def get_difficulty():
    """Get the current difficulty from the node."""
    try:
        response = requests.get(f"{NODE_URL}/difficulty")
        response.raise_for_status()
        return response.json().get('difficulty', '0000')
    except requests.exceptions.RequestException as e:
        print(Fore.RED + "Error getting difficulty:", e)
        return '0000'

def mine_block(previous_block):
    """Mine a new block."""
    current_difficulty = get_difficulty()
    nonce = 0

    while not stop_mining:
        # Create the block data
        block_data = {
            "nonce": nonce,
            "address": RECEIPT_ADDRESS
        }

        # Calculate the block hash
        block_string = json.dumps({**previous_block, **block_data}, sort_keys=True).encode()
        block_hash = hashlib.sha256(block_string).hexdigest()

        # Print the current nonce being tested
        print(f"Mining nonce: {nonce}")

        # Check if the block hash meets the difficulty requirement
        if block_hash.startswith(current_difficulty):
            block_data['hash'] = block_hash
            block_data['previous_hash'] = previous_block['hash']
            block_data['block_height'] = previous_block['block_height'] + 1
            block_data['timestamp'] = int(time.time())

            # Output mined block information
            print_block_info(block_data)
            submit_block(block_data)
            break

        nonce += 1

def submit_block(block_data):
    """Submit the mined block to the node."""
    try:
        response = requests.post(f"{NODE_URL}/mine", json=block_data)
        response.raise_for_status()
        print(Fore.GREEN + "Block confirmed!")
    except requests.exceptions.RequestException as e:
        print(Fore.RED + "Block Rejected:", e)

def print_block_info(block_data):
    """Print the mined block information."""
    print(Fore.GREEN + "Block Found!")
    print(f"Block Height: {block_data['block_height']}")
    print(f"Hash: {block_data['hash']}")
    print(f"Nonce: {block_data['nonce']}")
    print(f"Miner: {block_data['address']}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

def start_mining():
    """Start the mining process."""
    while not stop_mining:
        # Get the last block from the node
        response = requests.get(f"{NODE_URL}/previousblock")
        if response.status_code == 200:
            last_block = response.json()
            mine_block(last_block)
        else:
            print(Fore.RED + "Failed to retrieve the blockchain:", response.status_code)
        
        time.sleep(1)  # Sleep before the next mining attempt

def signal_handler(sig, frame):
    """Handle termination signal to stop mining gracefully."""
    global stop_mining
    stop_mining = True
    print(Fore.YELLOW + "\nStopping mining process...")

if __name__ == '__main__':
    # Set up signal handler for graceful shutdown on Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    print(Fore.BLUE + "Starting the mining process...")
    start_mining()
