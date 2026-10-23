"""Replay a delivered BIN's native A/B UI -> queue -> physical Live DISP.
Original Base filtering, packet decoder, adapter, debounce and native navigation
payload execute ARM. Model/file IO/native list APIs and enqueue are boundaries;
this does not emulate camera hardware, LCD, or capture workers.
"""
import argparse,json,struct
from pathlib import Path
from tests.test_gr3_native_ab_switch import NativeSwitchTests
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *

def probe(folder):
 folder=Path(folder);m=json.loads((folder/'gr3/manifest.json').read_text())
 NativeSwitchTests.appended_slots=bool(m['appended_slots']);NativeSwitchTests.setUpClass()
 t=NativeSwitchTests();u=t.begin();u.mem_write(0x53000000,(folder/'evidence/final-rtos.bin').read_bytes())
 t.externals.update(m['symbols']);t.call(u,'top_ctor',t.owner)
 t.stock_input_gate(u);t.real_navigation=True
 state=bytes.fromhex(m['initial_state_hex']);queue=[];stock=[];seen=[];native_ok=[False];confirm_states=[]
 no_live_ui=[False];delegated_live=[];native_menu=[]
 forbidden={0x536af2a8,0x536af2e4,0x53390ca0,0x53390ef8,0x533aba64,0x533ad3c0,0x533ad308,0x5316cde8}
 forbidden.update(m['symbols'][n] for n in ('m10v_debug_log','m10v_debug_batch'))
 originals={a:n for n,a in m['settings_menu']['exports'].items() if n.startswith('m10v_ab_') and n!='m10v_ab_dispatch_original'}
 def boundary(uc,at,n,_):
  r=[uc.reg_read(reg) for reg in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
  seen.append(at)
  if no_live_ui[0] and at in forbidden:raise AssertionError('A/B live UI API reached: '+hex(at))
  if at==m['symbols']['m10v_camera_library_load']:uc.mem_write(r[0],state);value=0
  elif at in (m['symbols']['m10v_debug_log'],m['symbols']['m10v_debug_batch']):value=1
  elif at in originals:
   stock.append(originals[at])
   if originals[at]=='m10v_ab_live_event_original':delegated_live.append(int.from_bytes(uc.mem_read(r[1],2),'little'))
   if originals[at]=='m10v_ab_selector_original':native_menu.append(r[1])
   if native_ok[0] and originals[at]=='m10v_ab_adj_event_original':
    confirm_states.append(t.word(uc,t.page+0x284+8));return # execute real native OK -> queue86
   value=0
  elif at==0x536af2a8:value=0x55090000
  elif at==0x532288b0:
   queue.append({'event':r[1],'payload':list(struct.unpack('<2I',uc.mem_read(r[2],8))) if r[2] else None,'source':r[3]});value=1
  else:return
  uc.reg_write(UC_ARM_REG_R0,value);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 u.hook_add(UC_HOOK_CODE,boundary)
 def key(k):t.call(u,0x5316d5dc,t.controller,t.event(u,k))
 def physical(phase,repeats):t.call(u,0x5316d5dc,t.controller,t.physical(u,phase,repeats))
 physical(1,1);physical(2,0)
 # Select stock Standard for A; B defaults to native Hi-Contrast B&W.
 initial=12 if m['appended_slots'] else 1
 for _ in range((m['settings_menu']['ab_host']['choices']-initial)%m['settings_menu']['ab_host']['choices']):key(0xd1)
 key(0xd8);key(0xd8)
 assert t.ab_tone==11,t.ab_tone
 assert [q['payload'] for q in queue if q['event']==0x193]==[[0x08000000,0x10000000]],queue
 assert 0x5316c9d8 in seen and 0x5316ccf8 in seen and 0x5323bc4c in seen
 # The scheduler/Live controller construction is a boundary; commit the route.
 u.mem_write(t.controller+4,bytes(4))
 t.route=0x08000000;u.mem_write(t.controller+0x124,struct.pack('<I',t.route))
 vt=0x5507e200;u.mem_write(t.controller,struct.pack('<I',vt));u.mem_write(vt+0x28,struct.pack('<I',0x531771c0))
 t.physical_mapper=0x5507e000;u.mem_write(t.physical_mapper,struct.pack('<I',0x5507e100));u.mem_write(0x5507e108,struct.pack('<I',0x532231e4))
 u.mem_write(0x55078520,b'\1')
 tones=[t.ab_tone];physical(1,1);tones.append(t.ab_tone)
 physical(1,1);physical(2,1);assert t.ab_tone==16
 physical(2,0);physical(1,1);tones.append(t.ab_tone)
 assert tones==[11,16,11],tones
 assert 'm10v_ab_selector_original' not in stock and 'm10v_ab_mapper_original' not in stock,stock
 assert 0x53223520 in seen # native physical DISP decoder, not synthetic37 alone
 # Keep the session active while native MENU/ADJ switch packets and lifecycle
 # boundaries run. Native lifecycle implementations are stubs here; forbid all
 # extra allocation/view/deletion calls made by A/B around those boundaries.
 no_live_ui[0]=True;t.call(u,'ab_live_enter',t.controller,t.route,0)
 for event_id in (5,26,27): # exact stock names MENU, ADJP, ADJL
  for phase,repeats in ((1,1),(2,0)):
   e=t.physical(u,phase,repeats);u.mem_write(e,struct.pack('<H',event_id));t.call(u,0x5316d5dc,t.controller,e)
  u.mem_write(t.page+0x284+28,struct.pack('<4I',0x55061000,0x55061000,0,0))
  t.call(u,'ab_live_leave',t.controller)
  assert bytes(u.mem_read(t.page+0x284+28,16))==bytes(16)
  t.call(u,'ab_live_enter',t.controller,t.route,0)
 t.call(u,'ab_live_destroy',t.controller)
 active_events=list(delegated_live);delegated_live.clear()
 # The real Base phase filter may suppress the down edge. Compare with the
 # same native input path with A/B disabled, rather than assuming both phases
 # reach the virtual handler.
 u.mem_write(t.page+0x284+8,struct.pack('<I',0))
 for event_id in (5,26,27):
  for phase,repeats in ((1,1),(2,0)):
   e=t.physical(u,phase,repeats);u.mem_write(e,struct.pack('<H',event_id));t.call(u,0x5316d5dc,t.controller,e)
 assert active_events==delegated_live and set(active_events)=={5,26,27},(active_events,delegated_live)
 assert 0x39 in native_menu,native_menu # stock physical MENU-release decode
 no_live_ui[0]=False
 # Actual stock ADJ OK queues 0x86. Model selection and scheduler commit are
 # boundaries; test both same-tone confirmation and a changed native tone.
 native_ok[0]=True;confirmations=[]
 for chosen in (11,17):
  t.route=0x02000000;u.mem_write(t.controller,struct.pack('<I',0x53b394e0));u.mem_write(t.controller+0x124,struct.pack('<I',t.route))
  u.mem_write(t.page+0x284+8,struct.pack('<I',1));u.mem_write(t.page+0x284+16,struct.pack('<I',0));t.ab_tone=chosen
  no_live_ui[0]=True
  before=len(queue);key(0xd8)
  assert confirm_states[-1]==0,confirm_states
  assert [q['event'] for q in queue[before:]]==[0x86],queue[before:]
  t.route=0x08000000;t.call(u,'ab_live_enter',t.controller,t.route,0)
  assert t.word(u,t.page+0x284+8)==0 and t.word(u,t.page+0x284+28)==0
  assert t.ab_tone==chosen
  confirmations.append({'tone':chosen,'disabled_before_original_ok':True,'native_event':0x86,'no_stale_overlay_on_return':True})
 # Physical entry, release, exit, duplicate down and release while queued
 # navigation still reports ADJ must never reopen the just-closed picker.
 no_live_ui[0]=False
 native_ok[0]=False;t.route=0x02000000;u.mem_write(t.controller+0x124,struct.pack('<I',t.route))
 physical(2,0);physical(1,1);physical(2,0)
 assert t.word(u,t.page+0x1fc+4)==2 # native host attached
 before=len(queue);physical(1,1);physical(1,1);physical(2,0)
 assert t.word(u,t.page+0x1fc+4)==0
 assert [q['payload'] for q in queue[before:] if q['event']==0x193]==[[0x08000000,0x10000000]]
 return {'tones':tones,'queue':queue,'native_phase_gate_executed':True,'native_physical_decoder_executed':True,'native_disp_not_delegated_while_active':True,'native_live_switch_events_active':active_events,'native_live_switch_events_disabled':delegated_live,'native_menu_release_logical':0x39,'ab_live_ui_api_calls':0,'ab_navigation_diagnostic_calls':0,'native_lifecycle_is_boundary':True,'normal_adj_confirmations':confirmations,'physical_picker_exit_does_not_reopen':True,'journal_files':sorted(t.ab_files),'lcd_emulated':False,'hardware':False,'boundaries':__doc__}

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('folder');a=p.parse_args()
 print(json.dumps(probe(a.folder),indent=2))
