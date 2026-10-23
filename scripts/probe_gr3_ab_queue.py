"""Replay observed DISP DOWN + A1 through delivered stock BaseController dispatch.

Actual patched MENU/ADJ key handler, consumption branch, global fallback,
factory and navigation payload allocation execute ARM. Hardware model callbacks,
debug IO, ADJ slot getter and final queue enqueue are substituted. The A1 input
is supplied from real logs; its asynchronous hardware origin is not emulated.
This proves queue contents at this boundary, not LCD or camera operation.
Run with PYTHONPATH=. and M10V_GR3_ORIGINAL_RTOS set to official GR III RTOS.
"""
import argparse
import json
import struct
from pathlib import Path
from tests.test_gr3_settings_view import SettingsViewTests
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import *

def probe(folder, keys=(0x37,0xa1), adj=False, adj_type=12):
    folder=Path(folder); manifest=json.loads((folder/'gr3/manifest.json').read_text())
    t=SettingsViewTests();t.firmware=(folder/'evidence/fixed-rtos.bin').read_bytes();t.code=b'';t.card=b''
    u=t.machine(native_accessor=True);t.heap=0x55110000
    owner=0x55040000;page=owner+0x13bc;source=0x55050000;route=0x02000000 if adj else 0x02000012
    def word(a,v):u.mem_write(a,struct.pack('<I',v))
    word(0x55063910,1);word(0x55063988,owner);word(0x55063914+0x94,source)
    word(page,manifest['settings_menu']['vtable']);word(source,0x53b394e0 if adj else 0x53b3b618)
    # This entry probe models an already constructed TopMenu owner. Seed the
    # same nonzero default pair as top_ctor; do not use zeroed private state.
    word(page+0x284,12 if manifest.get('appended_slots') else 1);word(page+0x288,5)
    word(source+0x124,route);word(0x55008000,route)
    word(0x5500c000,0x5500c020);u.mem_write(0x5500c520,b'\0');u.mem_write(0x5500c020,struct.pack('<16I',*([0x5500c100]*16)))
    u.mem_write(0x5500c100,bytes.fromhex('0000a0e31eff2fe1'));word(0x5500c200,0x53b4ddf8)
    native_host=manifest.get('settings_menu',{}).get('ab_host',{}).get('stage') in ('read-only','compare')
    ui=[]
    if adj and native_host:
        word(0x55060000+0xf4,0x55074000);word(0x55060000+0xf8,0x55074000+24*4)
        word(source+4,0x55061000);word(source+0x15c,0x55061000)
        for offset,value in [(0x160,0x55062000),(0x164,0x55063000),(0x168,0x55064000),(0x1ac,0x55065000),(0x1f0,0x55060000)]:word(source+offset,value)
        word(0x55060000,0x55066000);word(0x55066018,0x55067000)
        u.mem_write(0x55067000,bytes.fromhex('1eff2fe1'))
    queue=[];fallback=[];current=[0]
    getters={0x5320b19c,0x5320b73c,0x5320b8bc,0x5320b13c,0x5320b3dc,0x5320b07c,
             0x5320ae3c,0x5320bcdc,0x5320c03c,0x5320b1fc,0x5320c120,0x5320addc,0x5320af5c}
    callbacks={0x53229464,0x5322ae44,0x532b2618,0x5322ce9c,0x532ae708}
    def boundary(m,a,n,_):
        r=[m.reg_read(v) for v in (UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3)]
        if a==0x5316d804:fallback.append(current[0]);return
        if a==0x5320ad88:v=0x55007000
        elif a==0x5320aefc:v=0x55008000
        elif a==0x5320ba9c:v=0x55068200
        elif a==0x5320afbc:v=0x55009000
        elif a==0x5320b79c:v=0x5500c200
        elif a in getters:v=0x5500c000
        elif a in callbacks:v=0
        elif a==0x531a2820:v=adj_type
        elif native_host and a==manifest['symbols']['m10v_camera_library_load']:
            m.mem_write(r[0],bytes.fromhex(manifest['initial_state_hex']));v=0
        elif native_host and a==0x53828014:v=0
        elif native_host and a==0x533947f0:word(r[1],2);word(r[2],0);v=0
        elif native_host and a==0x53394758:v=0x55070000+r[1]*0x200
        elif native_host and a==0x533948c4:v=300
        elif native_host and a in (0x53394e8c,0x533a1808,0x533a1734,0x533a18e0,0x533a19b4,0x53395430,0x53395260,0x53396f80,0x533ad3c0,0x533ad308,0x53395224):ui.append([a,*r[:3]]);v=0
        elif a==manifest['symbols']['m10v_debug_log']:v=1
        elif a==0x532288b0:
            queue.append({'event':r[1],'payload':list(struct.unpack('<2I',m.mem_read(r[2],8))) if r[2] else None,'source':r[3]});v=1
        else:return
        m.reg_write(UC_ARM_REG_R0,v);m.reg_write(UC_ARM_REG_PC,m.reg_read(UC_ARM_REG_LR))
    u.hook_add(UC_HOOK_CODE,boundary)
    for key in keys:
        physical=isinstance(key,(tuple,list))
        current[0]=key
        u.mem_write(0x55000100,struct.pack('<HHI',4 if physical else key,0,0x55000200 if physical else 0))
        if physical:u.mem_write(0x55000200,struct.pack('<2I',*key))
        u.reg_write(UC_ARM_REG_R0,source);u.reg_write(UC_ARM_REG_R1,0x55000100)
        u.reg_write(UC_ARM_REG_SP,0x100f0000);u.reg_write(UC_ARM_REG_LR,0x10000000)
        try:u.emu_start(0x5316d5dc,0x10000000,count=2000000)
        except Exception as e:raise RuntimeError({'pc':hex(u.reg_read(UC_ARM_REG_PC)),'lr':hex(u.reg_read(UC_ARM_REG_LR)),'r0':hex(u.reg_read(UC_ARM_REG_R0)),'r1':hex(u.reg_read(UC_ARM_REG_R1)),'r2':hex(u.reg_read(UC_ARM_REG_R2)),'key':key}) from e
        assert u.reg_read(UC_ARM_REG_PC)==0x10000000
    return {'entry':'adj' if adj else 'menu','keys':list(keys),'fallback':fallback,'queue':queue,'ui':ui,'hardware':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('folder')
    parser.add_argument('--expect-old-failure',action='store_true');args=parser.parse_args()
    SettingsViewTests.setUpClass()
    menu=probe(args.folder)
    native_host=json.loads((Path(args.folder)/'gr3/manifest.json').read_text()).get('settings_menu',{}).get('ab_host',{}).get('stage') in ('read-only','compare')
    full=json.loads((Path(args.folder)/'gr3/manifest.json').read_text());host=full['settings_menu'].get('ab_host',{})
    root_rows=(5 if full.get('appended_slots') else 6) if host.get('direct_pair') else 4 if host.get('stage')=='compare' else 3
    expected=[0x0200f104,1] if args.expect_old_failure else [0x02000000] if native_host else [0x0200f104]
    assert [e['payload'][0] for e in menu['queue'] if e['event']==0x193]==expected,menu
    results=[menu]
    if not args.expect_old_failure:
        assert not menu['fallback'],menu
        adj=probe(args.folder,adj=True);assert not adj['fallback'],adj
        assert [e['payload'][0] for e in adj['queue'] if e['event']==0x193]==([] if native_host else [0x0200f104]),adj
        if native_host:assert any(e[:3]==[0x53394e8c,0x55060000,root_rows] for e in adj['ui']),adj
        ordinary=probe(args.folder,keys=(0xa1,))
        assert [e['payload'][0] for e in ordinary['queue'] if e['event']==0x193]==[1],ordinary
        results.extend([adj,ordinary])
        if native_host and any(h['address']==0x5316d5dc for h in json.loads((Path(args.folder)/'gr3/manifest.json').read_text())['settings_menu']['ab_hooks']):
            physical=probe(args.folder,keys=((1,1),(2,0)),adj=True)
            assert any(e[:3]==[0x53394e8c,0x55060000,root_rows] for e in physical['ui']),physical
            other=probe(args.folder,keys=((1,1),(2,0)),adj=True,adj_type=8)
            assert not other['ui'] and not other['queue'],other
            results.extend([physical,other])
    print(json.dumps({'results':results,'boundaries':__doc__},indent=2))
