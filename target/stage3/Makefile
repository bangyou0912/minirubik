# Run these targets from the repository root.
CC ?= cc
CFLAGS ?= -O3 -std=c99 -Wall -Wextra
DIR := target/stage3
BUILD := $(DIR)/build
.PHONY: compare audit check sanitize
$(BUILD):
	mkdir -p $(BUILD)
compare:
	python3 $(DIR)/compare.py
audit: compare
	python3 $(DIR)/summarize.py
$(BUILD)/verify-all: $(DIR)/verify_all.c $(DIR)/search.c $(DIR)/joint.h solver.c | $(BUILD)
	$(CC) $(CFLAGS) $(DIR)/verify_all.c $(DIR)/search.c -o $@
check: $(BUILD)/verify-all
	/usr/bin/time -p -o $(DIR)/wall-time.txt $(BUILD)/verify-all > $(DIR)/all-state-verification.txt
	cat $(DIR)/all-state-verification.txt
	cat $(DIR)/wall-time.txt

$(BUILD)/sanity: $(DIR)/sanity.c $(DIR)/search.c $(DIR)/joint.h solver.c | $(BUILD)
	$(CC) -O1 -g -std=c99 -fsanitize=address,undefined -fno-omit-frame-pointer $(DIR)/sanity.c $(DIR)/search.c -o $@
sanitize: $(BUILD)/sanity
	$(BUILD)/sanity > $(DIR)/sanitizer-verification.txt
	cat $(DIR)/sanitizer-verification.txt
