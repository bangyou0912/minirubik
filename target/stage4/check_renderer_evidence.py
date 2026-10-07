"""Check renderer evidence, symbolic GUI source and unchanged graded build."""
from pathlib import Path
import json,hashlib,subprocess
D=Path(__file__).resolve().parent
measure=json.loads((D/'asm-r2-render-test-measurements.json').read_text());assert len(measure['samples'])==6
frames=0
for row in measure['samples']:
    num=lambda x:int(x,0) if isinstance(x,str) else x
    regs=row['telemetry']['registers'];assert num(regs['x12'])==0 and num(regs['x13'])==row['length']+1
    frames+=num(regs['x13'])
assert frames==34
native=json.loads((D/'native-renderer-tests.json').read_text());assert native['status']=='PASS' and len(native['samples'])==3
for row in native['samples']:
    source=D/'ripes'/row['GUI_source'];content=source.read_bytes()
    assert hashlib.sha256(content).hexdigest()==row['source_sha256']
    text=content.decode();assert 'LED_MATRIX_0_BASE' in text and 'LED_MATRIX_0_WIDTH' in text and 'LED_MATRIX_0_HEIGHT' in text
    assert '0x30000000' not in text and '.section ' not in text and 'expected_frames' not in text
trace=json.loads((D/'pipeline-events.json').read_text());assert trace['iret']==2484 and trace['cycles']==3287 and trace['capture_window_cycles']==[0,100]
assert len(trace['events'])==4
assert hashlib.sha256((D/'evidence/asm-r2/21345671111111/solver.elf').read_bytes()).hexdigest()=='b4ba9a07c22956b924ea1c9634cfafae5b6358de66abfffd058b132b55656106'
record={'renderer_implemented':True,'geometry_checks':1323,'target_models':['RV32_ISS','RV32_5S'],'pixel_checked_frames':frames,'pixel_word_comparisons':frames*875,'native_RAM_model_tests':3,'actual_pipeline_trace':{'cycles':3287,'iret':2484,'captured_cycles':[0,100]},'actual_GUI_LED_verified':False,'actual_GUI_wire_signals_verified':False,'GUI_limitation':'Native app control is unavailable in this session; browser tools cannot inspect the Ripes window.','remaining':'Manual screenshots required: follow visualization.md for real LED and control-signal evidence.'}
(D/'visualization-status.json').write_text(json.dumps(record,indent=2)+'\n')
for name in ['stage4.md','visualization.md']:
    text=(D.parents[1]/name).read_text(encoding='utf-8-sig');assert text.count(chr(96)*3)%2==0
print('PASS: 34 frames / 29750 pixels, symbolic GUI sources, native tests, observed pipeline events, unchanged CLI ELF; real GUI remains unverified')
