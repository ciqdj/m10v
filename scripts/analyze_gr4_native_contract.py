"""Execute official GR IV recipe plans and JPEG-config creator instructions.

Synthetic objects and service assertion interception; no hardware is emulated.
"""
import hashlib
import struct
from scripts.analyze_gr4_capture import SHA256,BASE


def analyze(rtos):
    if hashlib.sha256(rtos).hexdigest()!=SHA256:
        raise ValueError('exact GR4 RTOS identity required')
    from unicorn import Uc,UC_ARCH_ARM,UC_MODE_ARM,UC_HOOK_CODE
    from unicorn import arm_const as r
    def machine():
        u=Uc(UC_ARCH_ARM,UC_MODE_ARM)
        u.mem_map(BASE,(len(rtos)+4095)&~4095);u.mem_write(BASE,rtos)
        u.mem_map(0x60000000,0x20000)
        u.reg_write(r.UC_ARM_REG_SP,0x6001f000);u.reg_write(r.UC_ARM_REG_LR,0x6001ff00)
        return u
    cases=[];allowed=[]
    for mode in range(17):
        u=machine();steps=[];assertions=[]
        def record(uc,address,size,context):
            if address==0x53712278:
                steps.append({'index':uc.reg_read(r.UC_ARM_REG_R1),
                    'kind':uc.reg_read(r.UC_ARM_REG_R2),'module':uc.reg_read(r.UC_ARM_REG_R3),
                    'extra':struct.unpack('<I',uc.mem_read(uc.reg_read(r.UC_ARM_REG_SP),4))[0]})
            if address==0x538ed930:
                assertions.append(bool(uc.reg_read(r.UC_ARM_REG_R0)))
                uc.reg_write(r.UC_ARM_REG_PC,uc.reg_read(r.UC_ARM_REG_LR))
        u.hook_add(UC_HOOK_CODE,record)
        u.reg_write(r.UC_ARM_REG_R0,0x60000000);u.reg_write(r.UC_ARM_REG_R1,mode)
        u.emu_start(0x53712b9c,0x6001ff00,count=100000)
        if u.reg_read(r.UC_ARM_REG_PC)!=0x6001ff00:raise ValueError('planner budget exceeded')
        def starts(module):return [i for i,x in enumerate(steps) if x['kind']==1 and x['module']==module]
        producer,jpeg=starts(26),starts(6)
        # GR4 has a completion-delivery step kind11 preceding the kind10 barrier.
        def waits(i):
            j=i+1
            if j<len(steps) and steps[j]['kind']==11:j+=1
            return i+1<len(steps) and steps[i+1]['kind']==11
        pw=bool(producer and jpeg and producer[-1]<jpeg[-1] and waits(producer[-1]))
        jw=bool(jpeg and waits(jpeg[-1]))
        cleanup=bool(jpeg and all(any(i>jpeg[-1] and x['kind']==3 and x['module']==m
            for i,x in enumerate(steps)) for m in (5,6)))
        case={'mode':mode,'steps':steps,'producer_waits':pw,'jpeg_waits':jw,'cleanup_after_jpeg':cleanup,'assertions':assertions}
        cases.append(case)
        if pw and jw and cleanup and all(assertions):allowed.append(mode)
    # Exact setup case6 writes the descriptor/request/shooting links. Only its
    # ordinary descriptor copy is intercepted; the field writes execute stock.
    u=machine();recipe=0x60000000;request=0x60006000;shooting=0x60008000
    u.mem_write(recipe+0x5c,struct.pack('<I',request));u.mem_write(recipe+0x4688,struct.pack('<I',shooting))
    u.reg_write(r.UC_ARM_REG_R0,recipe);u.reg_write(r.UC_ARM_REG_R4,recipe)
    def copied(uc,address,size,context):
        if address==0x538d336c:
            dst,src=(uc.reg_read(v) for v in (r.UC_ARM_REG_R0,r.UC_ARM_REG_R1))
            uc.mem_write(dst,bytes(uc.mem_read(src,32)))
            uc.reg_write(r.UC_ARM_REG_PC,uc.reg_read(r.UC_ARM_REG_LR))
    u.hook_add(UC_HOOK_CODE,copied)
    u.emu_start(0x5370f7b0,0x5370f818,count=1000)
    def word(at):return struct.unpack('<I',u.mem_read(at,4))[0]
    creator={'main_descriptor':word(recipe+0xb9c)-recipe,'request':word(recipe+0xb98),
        'shooting':word(recipe+0xb94),'status':word(recipe+0xb90)-recipe,
        'preview':word(recipe+0xba8)-recipe,'jpeg':word(recipe+0xbac)-recipe}
    return {'schema':'m10v-gr4-native-contract/v1','rtos_sha256':SHA256,
        'allowed_modes':allowed,'modes':cases,'creator':creator,
        'config_offset':0xb60,'shooting_offset':0x4688,
        'hardware':'not_tested','limits':['Synthetic recipe dimensions and addresses.',
            'Assertion service and descriptor copy intercepted; scheduler/hardware not emulated.']}
