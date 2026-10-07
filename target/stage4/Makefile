CC ?= cc
DIR := target/stage4
BUILD := $(DIR)/build
.PHONY: cases extra-cases reference assembly ripes
$(BUILD):
	mkdir -p $(BUILD)
$(BUILD)/make-cases: $(DIR)/make_cases.c solver.c | $(BUILD)
	$(CC) -O3 -std=c99 $(DIR)/make_cases.c -o $@
$(BUILD)/make-extra-cases: $(DIR)/make_extra_cases.c solver.c | $(BUILD)
	$(CC) -O3 -std=c99 $(DIR)/make_extra_cases.c -o $@
cases: $(BUILD)/make-cases
	$(BUILD)/make-cases
extra-cases: $(BUILD)/make-extra-cases
	$(BUILD)/make-extra-cases
reference: cases
	python3 $(DIR)/build_reference.py --vector 12345671111111 --expect 0
	python3 $(DIR)/build_reference.py --vector 26471352122222 --expect 3
	python3 $(DIR)/build_reference.py --vector 21345671111111 --expect 11
assembly: cases
	python3 $(DIR)/build_assembly.py --revision 2 --vector 12345671111111 --expect 0
	python3 $(DIR)/build_assembly.py --revision 2 --vector 26471352122222 --expect 3
	python3 $(DIR)/build_assembly.py --revision 2 --vector 21345671111111 --expect 11
ripes: cases
	python3 $(DIR)/export_ripes.py --vector 12345671111111 --expect 0
	python3 $(DIR)/export_ripes.py --vector 26471352122222 --expect 3
	python3 $(DIR)/export_ripes.py --vector 21345671111111 --expect 11

.PHONY: renderer gui
$(BUILD)/generate-renderer: $(DIR)/generate_renderer.c $(DIR)/../stage3/search.c solver.c | $(BUILD)
	$(CC) -O2 -std=c99 $(DIR)/generate_renderer.c $(DIR)/../stage3/search.c -o $@
renderer: $(BUILD)/generate-renderer
	$(BUILD)/generate-renderer > $(DIR)/renderer-geometry-verification.txt
	cat $(DIR)/renderer-geometry-verification.txt
gui: renderer
	python3 $(DIR)/export_ripes.py --render --output solver-gui.s
	python3 $(DIR)/export_ripes.py --render --delay 0 --vector 26471352122222 --expect 3 --output walkthrough-gui.s
	python3 $(DIR)/export_ripes.py --render --delay 0 --vector 12345671111111 --expect 0 --output solved-gui.s
