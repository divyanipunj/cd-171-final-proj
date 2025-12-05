PORT1 ?= 8001
PORT2 ?= 8002
PORT3 ?= 8003
PORT4 ?= 8004
PORT5 ?= 8005

.PHONY: run_nodes stop

run_nodes:
	python3 node.py -port $(PORT1) -node 1 & echo $$! > pids.txt; \
	sleep 1; \
	python3 node.py -port $(PORT2) -node 2 & echo $$! >> pids.txt; \
	sleep 1; \
	python3 node.py -port $(PORT3) -node 3 & echo $$! >> pids.txt; \
	sleep 1; \
	python3 node.py -port $(PORT4) -node 3 & echo $$! >> pids.txt; \
	sleep 1; \
	python3 node.py -port $(PORT5) -node 3 & echo $$! >> pids.txt; \

stop:
	@echo "Killing processes..."
	@kill -9 `cat pids.txt 2>/dev/null` 2>/dev/null || true
	@rm -f pids.txt