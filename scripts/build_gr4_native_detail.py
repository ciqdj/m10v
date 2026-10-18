"""Exact GR IV 1.11 stock detail lifecycle relocation for unified runtime.
Hook preimages are locked to the decoded official RTOS SHA-256.
No old standalone state/allocator hooks are included.
"""
import hashlib, struct
from scripts.build_gr3_menu_patches import assembly, branch, movw
BASE=0x53000000
RTOS_SHA256="a9a9a51530c35819df47dee1cce9f4f560a17eeed1da258950167d282884fce1"
FIELDS=['Halation Gain','Halation Spread','Highlight Gate','Film Grain','Soft Diffusion','Grain Size','Leak Gain','Leak Position','Leak Spread','Leak Variation','RED Exposure']
DETAIL_IDS={'halo':list(range(19,29)),'common':list(range(22,29)),'red':list(range(22,30))}
STOCK_TABLE_ADDRESS=0x53d9a458
STOCK_CAPTIONS_ADDRESS=0x53d9a724


def build_detail(base,symbols,rtos=None):
 if rtos is None:
  from pathlib import Path
  rtos=Path("data/research/gr4/RTOS.bin").read_bytes()
 if hashlib.sha256(rtos).hexdigest()!=RTOS_SHA256:raise ValueError("detail requires exact official GR4 RTOS")
 table_bytes=rtos[STOCK_TABLE_ADDRESS-BASE:STOCK_TABLE_ADDRESS-BASE+640]
 if len(table_bytes)!=640:raise ValueError("GR4 detail table absent")
 image=bytearray();entries={};blocks=[]
 def data(raw,label):
  image.extend(bytes(-len(image)&3));a=base+len(image);image.extend(raw);blocks.append([a,a+len(raw),label]);return a
 def stub(text,label):
  image.extend(bytes(-len(image)&3));a=base+len(image);return data(assembly(text,a),label)
 def addr(reg,a):return f'movw {reg},#{a&65535};movt {reg},#{a>>16};'
 # Clone every stock kind, append only the current film's supported IDs.
 # Runtime validation selects the halo/common/RED table for each carrier.
 # Original stock tones outside the five carriers retain their original lists.
 # Dynamic resolution returns this table or the untouched stock table.

 tables={}
 for variant,ids in DETAIL_IDS.items():
  table=bytearray(table_bytes)
  for i in range(80):
   a,n=struct.unpack_from('<II',table,i*8)
   raw=rtos[a-BASE:a-BASE+n*2];assert len(raw)==n*2 and 0<n<=12
   a=data(raw+bytes(sum(([0,x] for x in ids),[])),'detail '+variant+' list '+str(i))
   struct.pack_into('<II',table,i*8,a,n+len(ids))
  tables[variant]=data(table,'dynamic '+variant+' detail tables')
 table_address=tables['halo']
 # Existing resource extension occupies IDs786..910. Reuse its text descriptors
 # for three captions, Grain and Soft Diffusion, avoiding another global hook.
 caption_ids=[i+238 for i in [862,863,864,827,828,913,914,915,916,917,933]]
 captions=data(rtos[STOCK_CAPTIONS_ADDRESS-BASE:STOCK_CAPTIONS_ADDRESS-BASE+76]+b''.join(struct.pack('<HH',i,i) for i in caption_ids),'detail caption pairs')
 # Each call site has already saved LR in the genuine stock prologue.
 for name,reg,ui in [('table_ip','ip','r0'),('table_r3','r3','r0'),('table_selected','r3','r4')]:
  text='push {r0-r12,lr};mrs r0,cpsr;push {r0,r1};'+f'ldr r0,[sp,#{8+(0 if ui=="r0" else 16)}];bl {hex(symbols["m10v_detail_table"])};'
  offset=8+(12 if reg=='r3' else 48)
  text+=f'str r0,[sp,#{offset}];pop {{r0,r1}};msr cpsr_fs,r0;'
  # Both ip sites have live lr=20. BL destroys it before entering this shim.
  if reg=='ip':text+='mov lr,#20;'
  text+='pop {r0-r12,pc};'
  entries[name]=stub(text,name)
 # Constructor precedes tone selection; reserve stock max12 + max11 private rows.
 entries['capacity']=stub('mov r0,#23;bx lr','detail constructor capacity')
 control=symbols['m10v_detail_control']
 # The C gate checks actual ui[0x19c] carrier and validated journal.
 # Private IDs can only originate in our validated list, but all dispatches
 # revalidate as well; an invalid/stale row takes the exact stock fallback.
 def gate(idreg,ui,fallback):
  return f'sub ip,{idreg},#19;cmp ip,#10;bhi {hex(fallback)};push {{r0-r3,r12,lr}};mov r0,{ui};bl {hex(symbols["m10v_detail_table"])};'+addr('ip',0x53d9a458)+'cmp r0,ip;pop {r0-r3,r12,lr};beq '+hex(fallback)+';'
 # Intercept before the stock computed branch, restore its original R0-R3,
 # IP/LR and CMP flags, and retain its exact 19-entry handler jump table.
 # This enforces native icon/value geometry for both private and stock rows.
 stock_handlers=struct.unpack('<19I',rtos[0x1ca45c:0x1ca45c+76])
 entries['row_dispatch']=stub('push {r0-r3,r12,lr};lsl r2,r3,#16;orr r2,r2,r4;mov r1,r5;mov r0,#8;'+f'bl {hex(control)};'+'pop {r0-r3,r12,lr};cmp r3,#18;ldrls pc,[pc,r3,lsl #2];b 0x531ca458;'+''.join('.word '+hex(a)+';' for a in stock_handlers),'row bounds and stock dispatch')
 entries['row']=stub(gate('r3','r5',0x531ca60c)+f'sub r2,r3,#19;lsl r2,r2,#16;orr r2,r2,r4;mov r1,r5;mov r0,#3;bl {hex(control)};b 0x531ca4b4','row render')
 entries['current']=stub(gate('r4','r5',0x531cab54)+f'sub r2,r4,#19;mov r1,r5;mov r0,#1;bl {hex(control)};mov r4,r0;b 0x531ca9fc','current value')
 # Slider clones retain the stock callback closure and stock cancel/return.
 default=stub(f'mov r1,r0;mov r0,#4;mov r2,#0;b {hex(control)}','factory default')
 entries['default']=default
 def clone(maximum):
  image.extend(bytes(-len(image)&3));destination=base+len(image);start=0x531c70a0;stop=0x531c71e0
  mapping={a:destination+a-start+(8 if a>=0x531c716c else 0) for a in range(start,stop+4,4)}
  output=bytearray()
  for a in range(start,stop,4):
   at=mapping[a]
   if a==0x531c716c:output+=struct.pack('<II',0xe3500000,branch(at-4,mapping[0x531c71c4],condition=0))
   w=struct.unpack_from('<I',rtos,a-BASE)[0]
   if w&0x0e000000==0x0a000000:
    d=(w&0xffffff)<<2
    if d&(1<<25):d-=1<<26
    target=a+8+d;w=branch(at,mapping.get(target,target),bool(w&0x1000000),w>>28)
   if a==0x531c70d0:w=0xe1a00006
   if a==0x531c70d4:w=branch(at,default,True)
   if a==0x531c70d8:w=0xe1a00000
   if a==0x531c70f0 and maximum==3:w=0xe3a03039
   if a==0x531c7114:w=0xe3a02000|maximum
   if a==0x531c7118:w=movw(3,360//maximum)
   output+=struct.pack('<I',w)
  return data(output,'stock slider clone '+str(maximum))
 sliders={n:clone(n) for n in (8,3,2,5,1)}
 # Private IDs keep stable meanings across the three visible lists.
 # Restore the original setup frame before dispatch; retain the selected ID
 # in ip because r0 must be the stock controller for the slider constructor.
 dispatch=''
 for id in range(19,30):
  maximum=[8,8,8,3,3,2,8,5,8,1,2][id-19]
  dispatch+=f'cmp ip,#{id};beq {hex(sliders[maximum])};'
 dispatch_stub=stub(dispatch+f'b {hex(sliders[8])}','slider dispatch')
 entries['setup']=stub(gate('r0','r4',0x531cad30)+f'mov ip,r0;mov r0,r4;sub sp,fp,#0x10;ldm sp,{{r4,fp,sp,lr}};b {hex(dispatch_stub)}','setup dispatch')
 entries['callback']=stub(gate('r5','r4',0x531cb4e8)+f'sub r2,r5,#19;lsl r2,r2,#8;orr r2,r2,r6;mov r1,r4;mov r0,#2;bl {hex(control)};cmp r0,#0;bne 0x531cb2f4;sub sp,fp,#0x1c;ldm sp,{{r4,r5,r6,r7,fp,sp,pc}}','immediate callback')

 entries['reset']=stub('push {r4,lr};bl 0x533b7100;mov r1,r5;mov r0,#7;mov r2,#0;'+f'bl {hex(control)};pop {{r4,pc}}','preserve stock reset')
 patches=[]
 def patch(a,raw,label):patches.append({'address':a,'expected':rtos[a-BASE:a-BASE+len(raw)].hex(),'replacement':raw.hex(),'label':label})
 def word(a,w,label):patch(a,struct.pack('<I',w),label)
 for a,name in [(0x531c9e64,'table_ip'),(0x531c9f0c,'table_r3'),(0x531ca3f4,'table_ip'),(0x531ca658,'table_selected')]:
  word(a,branch(a,entries[name],True),'detail table resolver')
 word(0x531c6dd0,branch(0x531c6dd0,entries['reset'],True),'detail reset journal')
 word(0x531ca450,branch(0x531ca450,entries['row_dispatch']),'detail row dispatch')
 word(0x531ca458,branch(0x531ca458,entries['row']),'detail private row')
 word(0x531ca994,branch(0x531ca994,entries['current']),'detail private current')
 word(0x531caba4,branch(0x531caba4,entries['setup']),'detail private slider')
 word(0x531cb278,branch(0x531cb278,entries['callback']),'detail private callback')
 word(0x531ca088,0xe3a00017,'detail row capacity')
 word(0x531ca76c,0xe350001d,'detail caption range')
 word(0x531ca7c0,movw(3,captions&65535),'detail captions low')
 word(0x531ca7c4,movw(3,captions>>16,True),'detail captions high')
 return bytes(image),{'patches':patches,'schema':'m10v-gr4-native-detail/v1','tables':table_address,'captions':captions,'entries':entries,'fields':FIELDS,'ids':list(range(19,30)),'variant_ids':DETAIL_IDS,'variant_tables':tables,'backend':'m10v_camera_library_detail','blocks':blocks,'slider8':sliders[8],'slider3':sliders[3],'sliders':sliders,'slider_dispatch':dispatch_stub,'table_symbol':'m10v_detail_tables','lifecycle':'stock immediate callback; cancel exits without rollback','row_icons':[500,488,413,493,595,1092,424,596,381,50,647],'row_values':'numeric stock slider index; RED EI125/64/250','row_value_rect':[50,10,40,40],'red_value_rect':[50,10,60,40],'camera_tested':False}
