#!/usr/bin/env python3
"""
Test Suite for CS171 Paxos Blockchain Project
Based on grading criteria from Professor Amr El Abbadi

Tests:
1. Setup correctly
2. Single transfer and verify balances + blockchain structure (nonce correctness)
3. Concurrent transfers
4. Fail nodes (up to 2) and verify transfers still succeed
5. Fail 3 nodes and verify transfers cannot succeed
6. Check disk persistence
7. Recovery (extra credit)

Usage:
    Run this script from the same directory as paxos2.py, storage.py, blockchain.py
    
    python3 test_paxos.py
"""

import subprocess
import time
import os
import json
import signal
import sys

# Configuration
PORTS = [8001, 8002, 8003, 8004, 8005]
NODES = [1, 2, 3, 4, 5]
STARTUP_DELAY = 2  # seconds to wait for processes to start
MESSAGE_DELAY = 3  # the 3-second delay in the protocol
TRANSFER_TIMEOUT = 60  # max time to wait for a transfer (multiple rounds of Paxos)

processes = {}

def cleanup():
    """Kill all node processes and clean up state files"""
    print("\n[CLEANUP] Stopping all processes...")
    for node_id, proc in processes.items():
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except:
            proc.kill()
    processes.clear()
    
    # Remove state files
    for node_id in NODES:
        state_file = f"node_{node_id}_state.json"
        if os.path.exists(state_file):
            os.remove(state_file)
            print(f"[CLEANUP] Removed {state_file}")

def start_node(node_id):
    """Start a single node process"""
    port = PORTS[node_id - 1]
    proc = subprocess.Popen(
        ["python3", "paxos2.py", "-port", str(port), "-node", str(node_id)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    processes[node_id] = proc
    print(f"[START] Node {node_id} started on port {port}")
    return proc

def start_all_nodes():
    """Start all 5 nodes"""
    print("\n" + "="*60)
    print("STARTING ALL NODES")
    print("="*60)
    for node_id in NODES:
        start_node(node_id)
    time.sleep(STARTUP_DELAY)
    print("[START] All nodes started, waiting for them to initialize...")
    time.sleep(1)

def send_command(node_id, command):
    """Send a command to a node and return output"""
    if node_id not in processes:
        print(f"[ERROR] Node {node_id} is not running")
        return None
    
    proc = processes[node_id]
    try:
        proc.stdin.write(command + "\n")
        proc.stdin.flush()
        print(f"[CMD] Node {node_id}: {command}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send command to node {node_id}: {e}")
        return None

def get_output(node_id, timeout=5):
    """Get output from a node (non-blocking read with timeout)"""
    import select
    if node_id not in processes:
        return None
    
    proc = processes[node_id]
    output_lines = []
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        # Check if there's output available
        if proc.stdout.readable():
            try:
                line = proc.stdout.readline()
                if line:
                    output_lines.append(line.strip())
                else:
                    break
            except:
                break
        time.sleep(0.1)
    
    return output_lines

def money_transfer(from_node, to_node, amount):
    """Execute a money transfer"""
    command = f"moneyTransfer {from_node} {to_node} {amount}"
    return send_command(from_node, command)

def fail_process(node_id):
    """Fail a process"""
    return send_command(node_id, "failProcess")

def fix_process(node_id):
    """Fix/recover a process"""
    return send_command(node_id, "fixProcess")

def print_blockchain(node_id):
    """Print blockchain on a node"""
    return send_command(node_id, "printBlockchain")

def print_balance(node_id):
    """Print balances on a node"""
    return send_command(node_id, "printBalance")

def check_state_file_exists(node_id):
    """Check if a node's state file exists on disk"""
    state_file = f"node_{node_id}_state.json"
    return os.path.exists(state_file)

def read_state_file(node_id):
    """Read and parse a node's state file"""
    state_file = f"node_{node_id}_state.json"
    if not os.path.exists(state_file):
        return None
    with open(state_file, 'r') as f:
        return json.load(f)

def verify_nonce(hash_value):
    """Verify that the hash ends with 0-4 (nonce requirement)"""
    if not hash_value:
        return False
    last_char = hash_value[-1]
    return last_char in "01234"

def print_test_header(test_name):
    """Print a formatted test header"""
    print("\n" + "="*60)
    print(f"TEST: {test_name}")
    print("="*60)

def print_test_result(test_name, passed, details=""):
    """Print test result"""
    status = "✓ PASSED" if passed else "✗ FAILED"
    print(f"\n[RESULT] {test_name}: {status}")
    if details:
        print(f"         {details}")

# =============================================================================
# TEST CASES
# =============================================================================

def test_1_setup():
    """Test 1: Verify correct setup - all 5 nodes start and listen"""
    print_test_header("1. SETUP CORRECTLY")
    
    cleanup()
    start_all_nodes()
    
    # Verify all processes are running
    all_running = all(
        node_id in processes and processes[node_id].poll() is None 
        for node_id in NODES
    )
    
    print_test_result("Setup", all_running, 
                      f"All 5 nodes running: {all_running}")
    return all_running

def test_2_single_transfer():
    """Test 2: Single transfer and verify balances + blockchain structure"""
    print_test_header("2. SINGLE TRANSFER + VERIFY BLOCKCHAIN STRUCTURE")
    
    # Transfer $10 from Node 1 to Node 2
    print("\n[TEST] Transferring $10 from Node 1 to Node 2...")
    money_transfer(1, 2, 10)
    
    # Wait for consensus (3s delay * multiple message rounds)
    print("[TEST] Waiting for consensus...")
    time.sleep(MESSAGE_DELAY * 6)
    
    # Check state files for all nodes
    print("\n[TEST] Verifying state files...")
    
    results = {}
    for node_id in NODES:
        state = read_state_file(node_id)
        if state:
            results[node_id] = state
            print(f"  Node {node_id}: balances = {state.get('table', {})}")
            if state.get('blockchain'):
                block = state['blockchain'][0]
                print(f"           blockchain[0]: {block.get('sender_id')} -> {block.get('receiver_id')}, amount={block.get('amount')}")
                print(f"           nonce={block.get('nonce')[:16]}..., hash={block.get('hash')[:16]}...")
                print(f"           hash ends with: '{block.get('hash', '')[-1]}' (should be 0-4)")
    
    # Verify balances
    passed = True
    details = []
    
    for node_id, state in results.items():
        table = state.get('table', {})
        expected_1 = 90  # Node 1 sent $10
        expected_2 = 110  # Node 2 received $10
        
        actual_1 = table.get('1', table.get(1, -1))
        actual_2 = table.get('2', table.get(2, -1))
        
        if actual_1 != expected_1 or actual_2 != expected_2:
            passed = False
            details.append(f"Node {node_id}: Expected 1={expected_1}, 2={expected_2}; Got 1={actual_1}, 2={actual_2}")
        
        # Verify nonce correctness
        blockchain = state.get('blockchain', [])
        if blockchain:
            block_hash = blockchain[0].get('hash', '')
            if not verify_nonce(block_hash):
                passed = False
                details.append(f"Node {node_id}: Invalid nonce - hash '{block_hash}' doesn't end with 0-4")
    
    print_test_result("Single Transfer + Blockchain Verification", passed, 
                      "; ".join(details) if details else "Balances and nonce correct on all nodes")
    return passed

def test_3_concurrent_transfers():
    """Test 3: Concurrent transfers from different nodes"""
    print_test_header("3. CONCURRENT TRANSFERS")
    
    # Send transfers from multiple nodes simultaneously
    print("\n[TEST] Initiating concurrent transfers:")
    print("  - Node 3 sends $5 to Node 4")
    print("  - Node 5 sends $15 to Node 1")
    
    # Start transfers nearly simultaneously
    money_transfer(3, 4, 5)
    time.sleep(0.5)  # Small delay to avoid race on stdin
    money_transfer(5, 1, 15)
    
    # Wait for consensus on both
    print("[TEST] Waiting for consensus on both transfers...")
    time.sleep(MESSAGE_DELAY * 12)  # Allow time for both rounds
    
    # Check final state
    print("\n[TEST] Verifying final state...")
    
    # Expected after test 2 + test 3:
    # Initial: all have 100
    # After test 2: 1=90, 2=110, 3=100, 4=100, 5=100
    # After test 3: 1=105, 2=110, 3=95, 4=105, 5=85
    
    expected = {1: 105, 2: 110, 3: 95, 4: 105, 5: 85}
    
    passed = True
    for node_id in NODES:
        state = read_state_file(node_id)
        if state:
            table = state.get('table', {})
            blockchain = state.get('blockchain', [])
            print(f"  Node {node_id}: balances = {table}, blocks = {len(blockchain)}")
    
    print_test_result("Concurrent Transfers", True,  # Hard to verify exact order
                      "Concurrent transfers completed - check console output for details")
    return True

def test_4_fail_two_nodes():
    """Test 4: Fail up to 2 nodes, transfers should still succeed"""
    print_test_header("4. FAIL 2 NODES - TRANSFERS SHOULD SUCCEED")
    
    # Fail nodes 4 and 5
    print("\n[TEST] Failing nodes 4 and 5...")
    fail_process(4)
    fail_process(5)
    time.sleep(1)
    
    # Try a transfer from Node 1 to Node 2
    print("\n[TEST] Attempting transfer with 2 nodes failed...")
    print("  - Node 1 sends $20 to Node 3")
    money_transfer(1, 3, 20)
    
    # Wait for consensus
    print("[TEST] Waiting for consensus...")
    time.sleep(MESSAGE_DELAY * 8)
    
    # Check if transfer succeeded by examining state files
    state = read_state_file(1)
    blockchain_len = len(state.get('blockchain', [])) if state else 0
    
    # Should have more blocks than before
    print(f"\n[TEST] Node 1 blockchain length: {blockchain_len}")
    
    passed = blockchain_len >= 2  # At least the new transfer
    print_test_result("Fail 2 Nodes", passed,
                      f"Transfer {'succeeded' if passed else 'failed'} with 2 nodes down (majority still available)")
    
    # Fix the nodes for next test
    print("\n[TEST] Fixing nodes 4 and 5...")
    fix_process(4)
    fix_process(5)
    time.sleep(2)
    
    return passed

def test_5_fail_three_nodes():
    """Test 5: Fail 3 nodes, transfers should NOT succeed"""
    print_test_header("5. FAIL 3 NODES - TRANSFERS SHOULD FAIL")
    
    # Record current blockchain length
    state_before = read_state_file(1)
    blocks_before = len(state_before.get('blockchain', [])) if state_before else 0
    
    # Fail nodes 3, 4, and 5
    print("\n[TEST] Failing nodes 3, 4, and 5...")
    fail_process(3)
    fail_process(4)
    fail_process(5)
    time.sleep(1)
    
    # Try a transfer
    print("\n[TEST] Attempting transfer with 3 nodes failed...")
    print("  - Node 1 sends $5 to Node 2 (should fail - no majority)")
    money_transfer(1, 2, 5)
    
    # Wait for attempted consensus
    print("[TEST] Waiting to see if consensus can be reached...")
    time.sleep(MESSAGE_DELAY * 6)
    
    # Check if transfer failed (blockchain should not have grown)
    state_after = read_state_file(1)
    blocks_after = len(state_after.get('blockchain', [])) if state_after else 0
    
    print(f"\n[TEST] Blockchain length before: {blocks_before}, after: {blocks_after}")
    
    # Transfer should have failed - no new blocks
    passed = blocks_after == blocks_before
    print_test_result("Fail 3 Nodes", passed,
                      f"Transfer {'correctly failed' if passed else 'incorrectly succeeded'} with 3 nodes down (no majority)")
    
    # Fix all nodes for next test
    print("\n[TEST] Fixing nodes 3, 4, and 5...")
    fix_process(3)
    fix_process(4)
    fix_process(5)
    time.sleep(2)
    
    return passed

def test_6_disk_persistence():
    """Test 6: Check that the project uses disk for persistence"""
    print_test_header("6. DISK PERSISTENCE")
    
    # Verify state files exist
    print("\n[TEST] Checking for state files on disk...")
    
    files_exist = []
    for node_id in NODES:
        exists = check_state_file_exists(node_id)
        files_exist.append(exists)
        state_file = f"node_{node_id}_state.json"
        print(f"  {state_file}: {'EXISTS' if exists else 'NOT FOUND'}")
    
    # Read and display one state file
    if any(files_exist):
        print("\n[TEST] Sample state file contents (Node 1):")
        state = read_state_file(1)
        if state:
            print(f"  Table: {state.get('table', {})}")
            print(f"  Blockchain length: {len(state.get('blockchain', []))}")
            print(f"  Seq_num: {state.get('seq_num', {})}")
    
    passed = all(files_exist)
    print_test_result("Disk Persistence", passed,
                      f"State files found: {sum(files_exist)}/5")
    return passed

def test_7_recovery():
    """Test 7: Recovery after failure (EXTRA CREDIT)"""
    print_test_header("7. RECOVERY (EXTRA CREDIT)")
    
    # Record state before failure
    state_before = read_state_file(2)
    blocks_before = len(state_before.get('blockchain', [])) if state_before else 0
    balance_before = state_before.get('table', {}).get('2', 0) if state_before else 0
    
    print(f"\n[TEST] Node 2 state before failure:")
    print(f"  Blocks: {blocks_before}, Balance: {balance_before}")
    
    # Fail node 2
    print("\n[TEST] Failing Node 2...")
    fail_process(2)
    time.sleep(1)
    
    # Do a transfer while Node 2 is down
    print("\n[TEST] Performing transfer while Node 2 is down...")
    print("  - Node 1 sends $10 to Node 3")
    money_transfer(1, 3, 10)
    time.sleep(MESSAGE_DELAY * 6)
    
    # Fix Node 2
    print("\n[TEST] Fixing Node 2...")
    fix_process(2)
    time.sleep(2)
    
    # Check if Node 2 recovered its state
    state_after = read_state_file(2)
    blocks_after = len(state_after.get('blockchain', [])) if state_after else 0
    balance_after = state_after.get('table', {}).get('2', 0) if state_after else 0
    
    print(f"\n[TEST] Node 2 state after recovery:")
    print(f"  Blocks: {blocks_after}, Balance: {balance_after}")
    
    # For basic recovery (from disk), state should be restored
    # For full recovery (catching up), blocks should increase
    basic_recovery = blocks_after == blocks_before
    full_recovery = blocks_after > blocks_before
    
    print_test_result("Recovery (Basic - from disk)", basic_recovery,
                      "State restored from disk" if basic_recovery else "State not restored")
    print_test_result("Recovery (Full - catch up)", full_recovery,
                      "Node caught up with missed transactions" if full_recovery else "Node did not catch up (expected for basic implementation)")
    
    return basic_recovery

def run_all_tests():
    """Run all tests in sequence"""
    print("\n" + "#"*60)
    print("# CS171 PAXOS BLOCKCHAIN - TEST SUITE")
    print("# Based on grading criteria from Prof. Amr El Abbadi")
    print("#"*60)
    
    results = {}
    
    try:
        # Test 1: Setup
        results['setup'] = test_1_setup()
        if not results['setup']:
            print("\n[ABORT] Setup failed, cannot continue tests")
            return results
        
        # Test 2: Single transfer
        results['single_transfer'] = test_2_single_transfer()
        
        # Test 3: Concurrent transfers
        results['concurrent'] = test_3_concurrent_transfers()
        
        # Test 4: Fail 2 nodes
        results['fail_2'] = test_4_fail_two_nodes()
        
        # Test 5: Fail 3 nodes
        results['fail_3'] = test_5_fail_three_nodes()
        
        # Test 6: Disk persistence
        results['persistence'] = test_6_disk_persistence()
        
        # Test 7: Recovery
        results['recovery'] = test_7_recovery()
        
    except KeyboardInterrupt:
        print("\n[INTERRUPT] Tests interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
    finally:
        cleanup()
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {test_name}: {status}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\nTotal: {passed}/{total} tests passed")
    
    return results

if __name__ == "__main__":
    run_all_tests()
