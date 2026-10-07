#!/bin/sh
# Run from the repository root in Ubuntu/WSL; target measurements run on Windows.
set -eu
make -f target/stage2/Makefile quick
make -f target/stage3/Makefile compare
python3 target/stage3/summarize.py
make -f target/stage3/Makefile check sanitize
make -f target/stage4/Makefile reference assembly ripes extra-cases gui
python3 target/stage4/export_ripes.py --output solver.s
for revision in 0 1; do
    python3 target/stage4/build_assembly.py --revision "$revision" --vector 12345671111111 --expect 0
    python3 target/stage4/build_assembly.py --revision "$revision" --vector 26471352122222 --expect 3
    python3 target/stage4/build_assembly.py --revision "$revision" --vector 21345671111111 --expect 11
done
for pair in '12345671111111 0' '26471352122222 3' '21345671111111 11'; do
    set -- $pair
    python3 target/stage4/build_assembly.py --render-test --vector "$1" --expect "$2"
done
python3 target/stage4/audit_gui_static.py
python3 target/stage4/audit_tables.py
python3 target/stage4/check_rebuilt_sections.py
python3 target/stage4/check_evidence.py
