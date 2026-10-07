# Run from the repository root: make -f target/stage2/Makefile check
CC ?= cc
CFLAGS ?= -O3 -std=c99 -Wall -Wextra
DIR := target/stage2
BUILD := $(DIR)/build
.PHONY: generate check quick
$(BUILD):
	mkdir -p $(BUILD)
$(BUILD)/generate: $(DIR)/generate.c $(DIR)/search.c $(DIR)/joint.h solver.c | $(BUILD)
	$(CC) $(CFLAGS) $(DIR)/generate.c $(DIR)/search.c -o $@
$(BUILD)/verify: $(DIR)/verify.c $(DIR)/search.c $(DIR)/joint.h solver.c | $(BUILD)
	$(CC) $(CFLAGS) $(DIR)/verify.c $(DIR)/search.c -o $@
generate: $(BUILD)/generate
	$(BUILD)/generate > $(DIR)/generation.txt
	cat $(DIR)/generation.txt
quick: generate $(BUILD)/verify
	$(BUILD)/verify > $(DIR)/verification.txt
	cat $(DIR)/verification.txt
check: generate $(BUILD)/verify
	$(BUILD)/verify --all > $(DIR)/all-state-verification.txt
	cat $(DIR)/all-state-verification.txt
