"""Offline GR III hardware-parameter feasibility probe, NOT a firmware builder.

Executes original ImageTuning Make and its original R2Y writers. Python injects
candidate parameters at three named CPU boundaries in emulator-owned memory.
It never executes ISP pixels, submits hardware work, or claims camera fidelity.
"""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tests.test_gr3_isp_base import StockISP
from unicorn import UC_PROT_READ,UC_PROT_EXEC
from unicorn.arm_const import UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R4
RTOS_SHA='8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67'
BOUNDARIES={'matrix':0x536deecc,'post':0x536e4778,'curves':0x536e8be0}
ALLOWED=((0x140,0x152),(0x12a0,0x12b2),(0x2688,0x5088))

class ColorBackendProbe(StockISP):
    def __init__(self,rom,look=None,restore_cache=True):
        self.look=look;self.events=[];self.private_records=[];self.last_make=None
        self.restore_cache=restore_cache;self.gamma_snapshots=[]
        super().__init__(rom)
        self.u.mem_protect(0x53000000,(len(rom)+65535)&~65535,UC_PROT_READ|UC_PROT_EXEC)

    def call(self,at,*args):
        super().call(at,*args)
        if at==0x536dd8f0 and self.restore_cache and self.gamma_snapshots:
            # Research-only isolation experiment: output banks have already
            # been copied to info. Restore the pre-injection Gamma state and
            # let the original converter finish its normal cache contents.
            # A production wrapper needs its own ABI/lifetime/concurrency proof.
            snapshots=self.gamma_snapshots;self.gamma_snapshots=[]
            look=self.look;self.look=None
            try:
                for gamma,color_space,original in snapshots:
                    self.u.mem_write(gamma,original)
                    super().call(0x536e8be0,gamma,color_space)
            finally:self.look=look

    def service(self,u,pc,size,data):
        look=self.look
        if pc==0x536dd8f0:self.last_make=(u.reg_read(UC_ARM_REG_R0),u.reg_read(UC_ARM_REG_R1))
        if look is not None and pc==BOUNDARIES['matrix']:
            ctx=u.reg_read(UC_ARM_REG_R1)
            record=struct.unpack('<I',u.mem_read(ctx+8,4))[0]
            original=bytes(u.mem_read(record,64))
            private=self.alloc(64);matrix=self.alloc(32)
            u.mem_write(private,original)
            u.mem_write(matrix,struct.pack('<9h',*look['matrixQ13']))
            self.w32(private,matrix);self.w32(ctx+8,private)
            self.private_records.append((record,original))
            self.events.append({'phase':'matrix','pc':pc,'private_record':private})
        elif look is not None and pc==BOUNDARIES['post']:
            at=u.reg_read(UC_ARM_REG_R4)
            native=struct.unpack('<9I',u.mem_read(at,36))
            h=[(v&0x7ffff)-(0x80000 if v&0x40000 else 0) for v in native]
            p=look['postQ512']
            result=[(sum(h[r*3+k]*p[k*3+c] for k in range(3))+256)>>9 for r in range(3) for c in range(3)]
            if any(not -(1<<18)<=v<(1<<18) for v in result):
                raise ValueError('CSP intermediate exceeds signed19')
            if any(not -256<=v<=255 for v in result):
                raise ValueError('CSP hardware coefficient exceeds signed9')
            u.mem_write(at,struct.pack('<9I',*(v&0x7ffff for v in result)))
            self.events.append({'phase':'post','pc':pc,'native_csp':h,'composed_csp':result})
        elif look is not None and pc==BOUNDARIES['curves']:
            gamma=u.reg_read(UC_ARM_REG_R0)
            self.gamma_snapshots.append((gamma,u.reg_read(UC_ARM_REG_R1),bytes(u.mem_read(gamma,0x3240))))
            for channel,offset in enumerate((0x2a08,0x2c08,0x2e08)):
                base=struct.unpack('<256H',u.mem_read(gamma+offset,512))
                curve=look['curves'][channel];out=[]
                for v in base:
                    index=min(v>>6,255);fraction=v&63
                    out.append(curve[index] if index==255 else (curve[index]*(64-fraction)+curve[index+1]*fraction+32)>>6)
                u.mem_write(gamma+offset,struct.pack('<256H',*out))
            self.events.append({'phase':'curves','pc':pc,'gamma_object':gamma})
        super().service(u,pc,size,data)

    def globals_unchanged(self):
        return all(bytes(self.u.mem_read(at,len(before)))==before for at,before in self.private_records)


def run_probe(rom,look,*,stage=1,extra=None,restore_cache=True):
    if hashlib.sha256(rom).hexdigest()!=RTOS_SHA:raise ValueError('unsupported RTOS hash')
    ref=ColorBackendProbe(rom)
    baseline,shot,_=ref.make(11,stage,extra=extra)
    probe=ColorBackendProbe(rom,look,restore_cache=restore_cache)
    output,after,_=probe.make(11,stage,extra=extra)
    changed=[i for i,(a,b) in enumerate(zip(baseline,output)) if a!=b]
    outside=[i for i in changed if not any(lo<=i<hi for lo,hi in ALLOWED)]
    csp=[v&511 for v in struct.unpack_from('<9H',output,0x12a0)]
    csp=[v-512 if v>=256 else v for v in csp]
    matrix=[v&4095 for v in struct.unpack_from('<9H',output,0x140)]
    matrix=[v-4096 if v>=2048 else v for v in matrix]
    result={'stage':stage,'events':probe.events,'assertions':probe.assertions,
        'shooting_info_unchanged':shot==after,'shared_records_unchanged':probe.globals_unchanged(),
        'initialized_globals_match_stock':bytes(probe.u.mem_read(0x55000000,0x3a080))==bytes(ref.u.mem_read(0x55000000,0x3a080)),
        'changed_bytes':len(changed),'outside_allowed_offsets':outside,
        'matrix_registers_signed12':matrix,'csp_registers_signed9':csp,
        'r2y_sha256':hashlib.sha256(output).hexdigest(),
        'gamma_banks_sha256':hashlib.sha256(output[0x2688:0x5088]).hexdigest(),
        'gamma_cache_restoration':restore_cache,
        'scope':'native CPU parameter writers only; hardware pixels and latency unverified'}
    # First test real object reuse. A fresh constructor can hide cached curves.
    probe.look=None
    po,pi=probe.last_make;ro,ri=ref.last_make
    probe.call(0x536dd8f0,po,pi);ref.call(0x536dd8f0,ro,ri)
    reused=bytes(probe.u.mem_read(pi,0x9000));reused_ref=bytes(ref.u.mem_read(ri,0x9000))
    result['reused_object_next_standard_unchanged']=reused==reused_ref
    result['reused_object_difference_offsets']=[i for i,(a,b) in enumerate(zip(reused,reused_ref)) if a!=b]
    ref.cursor=probe.cursor
    reverted,si,_=probe.make(11,stage,extra=extra)
    stock,stock_si,_=ref.make(11,stage,extra=extra)
    result['next_standard_unchanged']=reverted==stock and si==stock_si
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rtos',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--ids',type=int,nargs='+',default=[34,35,37,65])
    args=p.parse_args();rom=args.rtos.read_bytes()
    if hashlib.sha256(rom).hexdigest()!=RTOS_SHA:p.error('unsupported RTOS hash')
    looks=json.loads((ROOT/'web/gr3/film-catalog.json').read_text())['looks']
    rows=[]
    for film in args.ids:
        if not 34<=film<=65:p.error('probe supports existing matrix/curve records34..65 only')
        for stage in (0,1):
            row=run_probe(rom,looks[film-34],stage=stage);row.update(film=film,name=looks[film-34]['name']);rows.append(row)
    report={'schema':'m10v-gr3-isp-color-feasibility/v1','rtos_sha256':RTOS_SHA,
        'analyzer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'firmware_emitted':False,'camera_tested':False,'hardware_pixels_executed':False,'rows':rows}
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'rows':len(rows),'all_parameter_checks':all(not r['assertions'] and not r['outside_allowed_offsets'] and r['shooting_info_unchanged'] and r['shared_records_unchanged'] and r['initialized_globals_match_stock'] and r['reused_object_next_standard_unchanged'] and r['next_standard_unchanged'] for r in rows),'out':str(args.out)}))
    return report
if __name__=='__main__':main()
