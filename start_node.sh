#!/bin/bash
# start_nodes.sh - Start all 5 Paxos nodes
# Run each command in a separate terminal window

echo "Starting all 5 nodes..."
echo "Run each of these commands in a separate terminal:"
echo ""
echo "Terminal 1: python3 paxos2.py -port 8001 -node 1"
echo "Terminal 2: python3 paxos2.py -port 8002 -node 2"
echo "Terminal 3: python3 paxos2.py -port 8003 -node 3"
echo "Terminal 4: python3 paxos2.py -port 8004 -node 4"
echo "Terminal 5: python3 paxos2.py -port 8005 -node 5"
echo ""
echo "Or run this script with 'source' to start them in background:"
echo ""

# Uncomment below to auto-start in background (not recommended for demo)
# python3 paxos2.py -port 8001 -node 1 &
# python3 paxos2.py -port 8002 -node 2 &
# python3 paxos2.py -port 8003 -node 3 &
# python3 paxos2.py -port 8004 -node 4 &
# python3 paxos2.py -port 8005 -node 5 &
