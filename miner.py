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
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

MINER_ID = 'miner1'  # Unique miner ID
NODE_URL = 'http://192.168.0.103:5001/api'  # Node URL
RECEIPT_ADDRESS = 'TXVGuTWdPx1KuMo98oZDAb6SgZvUV8FS6r'  # Recipient address
NUM_THREADS = 2  # Number of mining threads
NONCE_RANGE = 1000000  # Total range of nonce to explore
THREAD_NONCE_RANGE = NONCE_RANGE // NUM_THREADS  # Nonce range per thread

# Shared variable to hold mined block hash to avoid duplicate submissions
mined_blocks = set()
lock = threading.Lock()
stop_mining = False

# Initialize difficulty and adjustment settings
current_difficulty = '0000'  # Start with default difficulty
hash_adjustment = 0  # Tracks the current hash adjustment
adjustment_threshold = 2  # Number of rejections before adjusting the hash value
rejection_count = 0  # Count the number of rejected submissions

def get_difficulty():
    """Get the current difficulty from the node."""
    global current_difficulty
    try:
        response = requests.get(f"{NODE_URL}/difficulty")
        response.raise_for_status()  # Raise an error for bad responses
        current_difficulty = response.json().get('difficulty', '0000')
        return current_difficulty
    except requests.exceptions.RequestException as e:
        print(Fore.RED + "Error getting difficulty:", e)
        return '0000'  # Set a default difficulty

def mine_block(previous_block, thread_id, start_nonce, end_nonce):
    """Mine a new block within a specific nonce range."""
    global hash_adjustment, rejection_count
    nonce = random.randint(start_nonce, end_nonce)  # Start with a random nonce in the given range
    start_time = time.time()

    while not stop_mining:
        # Create the block data
        block_data = {
            "nonce": nonce,
            "hash": '',  # Hash will be calculated below
            "address": RECEIPT_ADDRESS
        }

        # Calculate the block hash
        block_string = json.dumps({**previous_block, **block_data}, sort_keys=True).encode()
        block_hash = hashlib.sha256(block_string).hexdigest()

        # Print the current nonce being tested
        print_nonce_box(nonce)

        # Check if the block hash meets the difficulty requirement
        if block_hash.startswith(current_difficulty) and (int(block_hash, 16) < (2 ** (256 - hash_adjustment))):
            end_time = time.time()
            elapsed_time = end_time - start_time
            speed = nonce / elapsed_time if elapsed_time > 0 else 0  # Calculate speed
            
            with lock:
                if block_hash not in mined_blocks:  # Prevent duplicate submissions
                    mined_blocks.add(block_hash)
                    block_data['hash'] = block_hash
                    block_data['previous_hash'] = previous_block['hash']
                    block_data['block_height'] = previous_block['block_height'] + 1
                    block_data['timestamp'] = int(time.time())

                    # Submit the mined block
                    submit_block(block_data, True)
                    # Clear the nonce display
                    clear_nonce_display()
                    # Output in a box format
                    print_block_info(block_data, speed)
            time.sleep(5)  # Wait for seconds before trying to mine again
            break
        elif block_hash.startswith(current_difficulty):
            # If the block is valid but hash is too high, count as rejection
            rejection_count += 1
            if rejection_count >= adjustment_threshold:
                hash_adjustment += 1  # Increase the threshold if too many rejections
                rejection_count = 0  # Reset the rejection count
                print(Fore.YELLOW + f"Adjusting hash threshold to {hash_adjustment}.")
        
        nonce = random.randint(start_nonce, end_nonce)  # Randomly choose a new nonce in the range

def generate_nonce_range_per_thread(thread_id, threads):
    """Generate random nonce range for each thread."""
    range_per_thread = NONCE_RANGE // threads
    random_start = random.randint(0, NONCE_RANGE - range_per_thread)
    random_end = random_start + range_per_thread
    return random_start, random_end

def print_nonce_box(nonce):
    """Print the current nonce being tested in a box format."""
    box_width = 35
    output = f"{Fore.YELLOW}┌{'─' * (box_width - 2)}┐\n" \
             f"{Fore.YELLOW}│ {'Mining {nonce}'.ljust(box_width - 2)}│\n" \
             f"{Fore.YELLOW}└{'─' * (box_width - 2)}┘"
    
    # Clear previous line output
    sys.stdout.write('\r' + output)
    sys.stdout.flush()  # Flush the output buffer

def clear_nonce_display():
    """Clear the nonce display by moving the cursor up and printing spaces."""
    box_width = 30
    # Move the cursor up and clear the nonce box
    sys.stdout.write(Fore.YELLOW + "\033[F" + " " * box_width + "\n")  # Clear the line above
    sys.stdout.write(Fore.YELLOW + "\033[F" + " " * box_width + "\n")  # Clear the nonce box
    sys.stdout.flush()  # Flush the output buffer

def submit_block(block_data, is_mined):
    """Submit the mined block to the node."""
    global hash_adjustment, rejection_count
    try:
        response = requests.post(f"{NODE_URL}/mine", json=block_data)
        response.raise_for_status()  # Raise an error for bad responses
        if is_mined:
            hash_adjustment = 0
            print(Fore.GREEN + "Block confirmed!")
    except requests.exceptions.RequestException as e:
        print(Fore.RED + "|Block Rejected |", response.text)

def print_block_info(block_data, speed):
    """Print the mined block information in a box format."""
    box_width = 100
    print(Fore.GREEN + "┌" + "─" * (box_width - 2) + "┐")
    print(Fore.GREEN + "│ " + f"Block Found!".ljust(box_width - 2) + "│")
    print(Fore.GREEN + "│ " + f"Block Height: {block_data['block_height']}".ljust(box_width - 2) + "│")
    print(Fore.GREEN + "│ " + f"Hash: {block_data['hash']}".ljust(box_width - 2) + "│")
    print(Fore.GREEN + "│ " + f"Nonce: {block_data['nonce']}".ljust(box_width - 2) + "│")
    print(Fore.GREEN + "│ " + f"Miner: {block_data['address']}".ljust(box_width - 2) + "│")
    print(Fore.GREEN + "│ " + f"Speed: {speed:.2f} h/s".ljust(box_width - 2) + "│")  # Speed info
    print(Fore.GREEN + "│ " + f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}".ljust(box_width - 2) + "│")
    print(Fore.GREEN + "└" + "─" * (box_width - 2) + "┘")

def start_mining():
    """Start the mining process."""
    while not stop_mining:
        # Get the last block from the node
        response = requests.get(f"{NODE_URL}/previousblock")  # Use the correct endpoint
        if response.status_code == 200:
            last_block = response.json()  # Get the block data directly from the response
            
            threads = []
            for thread_id in range(NUM_THREADS):
                # Generate random nonce range per thread
                start_nonce, end_nonce = generate_nonce_range_per_thread(thread_id, NUM_THREADS)
                thread = threading.Thread(target=mine_block, args=(last_block, thread_id, start_nonce, end_nonce))
                thread.start()
                threads.append(thread)

            for thread in threads:
                thread.join()  # Wait for threads to complete
        else:
            print(Fore.RED + "Failed to retrieve the blockchain:", response.status_code, response.text)  # Display status and raw response

        # Sleep before the next mining attempt
        time.sleep(1)

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
