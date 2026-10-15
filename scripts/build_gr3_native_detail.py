"""Exact GR III 2.10 stock detail lifecycle relocation for unified runtime.
Stock snapshots are verified against official RTOS again by the Node auditor.
No old standalone state/allocator hooks are included.
"""
import struct
from scripts.build_gr3_menu_patches import assembly, branch, movw
BASE=0x53000000
FIELDS=['Halation Gain','Halation Spread','Highlight Gate','Film Grain','Soft Diffusion']
STOCK_TABLE=bytes.fromhex('2c4cb35309000000f04ab35309000000144ab3530a000000104fb353090000008c4ab353090000005050b3530a0000000c50b35309000000ac4ab35309000000ec4fb3530a000000584eb3530a000000d049b35304000000b849b3530a000000f449b3530a000000644cb3530a000000784eb3530b000000104bb3530a000000544fb3530a000000304fb3530b000000944fb3530a0000001c4eb3530a000000ec4eb3530b000000844cb3530b000000444ab35305000000b44eb3530b000000f449b3530a000000644cb3530a000000784eb3530b000000104bb3530a000000544fb3530a000000304fb3530b000000944fb3530a0000001c4eb3530a000000ec4eb3530b000000844cb3530b000000444ab35305000000b44eb3530b000000')
STOCK_CAPTIONS=bytes.fromhex('e3011901e1011b01e2011d01da011f01db012101dc012301e5012501e9012f01e9012f0167012f01e9012f01e9013f01dd012701e4013701d9013101de013301e0013501f8000000')
STOCK_SLIDER=bytes.fromhex('0dc0a0e1f0d82de97c5705e3055445e304b04ce268d04de2003095e50060a0e10040a0e320300be55b7701eb9f7a01eb9811d6e5305904eb0afdffeb04408de50f30a0e300308de51420a0e30c208de5233ea0e310308de54020a0e314208de5c730a0e318308de50070a0e108408de50410a0e10820a0e32d30a0e354004be248c807eb093da0e30420a0e100308de50710a0e11e30a0e354004be258c807eb54004be20410a0e15dc807eb647196e554104be20700a0e19fc807eb5c400be50c00a0e37c0814eb0030a0e1d02f00e31b2345e30700a0e1002083e5042a0ce3044083e51a2345e3086083e564104be264300be55c390ce358200be51a3345e35c300be56efb07eb5c301be5040053e10300000a64004be20320a0e30010a0e133ff2fe120201be5003095e5030052e10100001a1cd04be2f0a89de8d1cb19eb')
STOCK_LISTS={1404259372: '0200020102020203020402050206020d000e', 1404259056: '0200020102020203020402050206020d000e', 1404258836: '020202030204020502060207020c020d000e000f', 1404260112: '020202030204020502060207020c020d000f', 1404258956: '020202030204020502060207020d000e000f', 1404260432: '020202030204020502060207020c020d000e000f', 1404260364: '0200020102020203020402050206020d000e', 1404258988: '0200020102020203020402050206020d000e', 1404260332: '02000201020202030204020502060208020d000e', 1404259928: '02000201020202030204020502060209020d000e', 1404258768: '02000201020a0010', 1404258744: '0200020102020203020402050206020b020d000e', 1404258804: '02110200020102020203020402050206020d000e', 1404259428: '02110200020102020203020402050206020d000e', 1404259960: '0211020202030204020502060207020c020d000e000f', 1404259088: '0211020202030204020502060207020c020d000f', 1404260180: '0211020202030204020502060207020d000e000f', 1404260144: '0211020202030204020502060207020c020d000e000f', 1404260244: '02110200020102020203020402050206020d000e', 1404259868: '02110200020102020203020402050206020d000e', 1404260076: '021102000201020202030204020502060208020d000e', 1404259460: '021102000201020202030204020502060209020d000e', 1404258884: '021102000201020a0010', 1404260020: '02110200020102020203020402050206020b020d000e'}

def build_detail(base,symbols):
 image=bytearray();entries={};blocks=[]
 def data(raw,label):
  image.extend(bytes(-len(image)&3));a=base+len(image);image.extend(raw);blocks.append([a,a+len(raw),label]);return a
 def stub(text,label):
  image.extend(bytes(-len(image)&3));a=base+len(image);return data(assembly(text,a),label)
 def addr(reg,a):return f'movw {reg},#{a&65535};movt {reg},#{a>>16};'
 # Clone every stock kind, append independent IDs only for a validated 800T
 # carrier. Dynamic resolution returns this table or the untouched stock table.
 table=bytearray(STOCK_TABLE)
 for i in range(36):
  a,n=struct.unpack_from('<II',table,i*8)
  raw=bytes.fromhex(STOCK_LISTS[a]);assert len(raw)==n*2
  a=data(raw+bytes(sum(([0,x] for x in range(18,23)),[])),'detail list '+str(i))
  struct.pack_into('<II',table,i*8,a,n+5)
 table_address=data(table,'dynamic 800T detail tables')
 # Existing resource extension occupies IDs786..910. Reuse its text descriptors
 # for three captions, Grain and Soft Diffusion, avoiding another global hook.
 caption_ids=[862,863,864,827,828]
 captions=data(STOCK_CAPTIONS+b''.join(struct.pack('<HH',i,i) for i in caption_ids),'detail caption pairs')
 # Each call site has already saved LR in the genuine stock prologue.
 for name,reg,ui in [('table_ip','ip','r0'),('table_r3','r3','r0'),('table_selected','r3','r4')]:
  text='push {r0-r12,lr};mrs r0,cpsr;push {r0,r1};'+f'ldr r0,[sp,#{8+(0 if ui=="r0" else 16)}];bl {hex(symbols["m10v_detail_table"])};'
  offset=8+(12 if reg=='r3' else 48)
  text+=f'str r0,[sp,#{offset}];pop {{r0,r1}};msr cpsr_fs,r0;'
  # Both ip sites have live lr=12. BL destroys it before entering this shim.
  if reg=='ip':text+='mov lr,#12;'
  text+='pop {r0-r12,pc};'
  entries[name]=stub(text,name)
 # Constructor runs before actual tone selection; allocate stock max11+5.
 entries['capacity']=stub('mov r0,#16;bx lr','detail constructor capacity')
 control=symbols['m10v_detail_control']
 # The C gate checks actual ui[0x198] tone + film33, never the old kind8 gate.
 # Private IDs can only originate in our validated list, but all dispatches
 # revalidate as well; an invalid/stale row takes the exact stock fallback.
 def gate(idreg,ui,fallback):
  return f'sub ip,{idreg},#18;cmp ip,#4;bhi {hex(fallback)};push {{r0-r3,r12,lr}};mov r0,{ui};bl {hex(symbols["m10v_detail_table"])};'+addr('ip',0x53b3488c)+'cmp r0,ip;pop {r0-r3,r12,lr};beq '+hex(fallback)+';'
 entries['row']=stub(gate('r3','r5',0x531b01ac)+f'sub r2,r3,#18;lsl r2,r2,#16;orr r2,r2,r4;mov r1,r5;mov r0,#3;bl {hex(control)};b 0x531b0064','row render')
 entries['current']=stub(gate('r4','r5',0x531b0594)+f'sub r2,r4,#18;mov r1,r5;mov r0,#1;bl {hex(control)};mov r4,r0;b 0x531b045c','current value')
 # Slider clones retain the stock callback closure and stock cancel/return.
 default=stub(f'mov r1,r0;mov r0,#4;mov r2,#0;b {hex(control)}','factory default')
 entries['default']=default
 def clone(maximum):
  image.extend(bytes(-len(image)&3));destination=base+len(image);start=0x531acfec;stop=0x531ad12c
  mapping={a:destination+a-start+(8 if a>=0x531ad0b4 else 0) for a in range(start,stop+4,4)}
  output=bytearray()
  for a in range(start,stop,4):
   at=mapping[a]
   if a==0x531ad0b4:output+=struct.pack('<II',0xe3500000,branch(at-4,mapping[0x531ad110],condition=0))
   w=struct.unpack_from('<I',STOCK_SLIDER,a-start)[0]
   if w&0x0e000000==0x0a000000:
    d=(w&0xffffff)<<2
    if d&(1<<25):d-=1<<26
    target=a+8+d;w=branch(at,mapping.get(target,target),bool(w&0x1000000),w>>28)
   if a==0x531ad01c:w=0xe1a00006
   if a==0x531ad020:w=branch(at,default,True)
   if a==0x531ad024:w=0xe1a00000
   # Match the stock grain slider: resource 57 and 120-pixel tick pitch.
   if a==0x531ad03c and maximum==3:w=0xe3a03039
   if a==0x531ad060:w=0xe3a02000|maximum
   if a==0x531ad064 and maximum==3:w=0xe3a03078
   output+=struct.pack('<I',w)
  return data(output,'stock slider clone '+str(maximum))
 slider8=clone(8);slider3=clone(3)
 entries['setup']=stub(gate('r0','r4',0x531b075c)+f'cmp r0,#21;mov r0,r4;sub sp,fp,#0x10;ldm sp,{{r4,fp,sp,lr}};blo {hex(slider8)};b {hex(slider3)}','setup dispatch')
 entries['callback']=stub(gate('r5','r4',0x531b0e48)+f'sub r2,r5,#18;lsl r2,r2,#8;orr r2,r2,r6;mov r1,r4;mov r0,#2;bl {hex(control)};cmp r0,#0;bne 0x531b0c6c;sub sp,fp,#0x1c;ldm sp,{{r4,r5,r6,r7,fp,sp,pc}}','immediate callback')
 entries['reset']=stub('push {r4,lr};bl 0x532c282c;mov r1,r5;mov r0,#7;mov r2,#0;'+f'bl {hex(control)};pop {{r4,pc}}','preserve stock reset')
 return bytes(image),{'schema':'m10v-gr3-native-detail/v1','tables':table_address,'captions':captions,'entries':entries,'fields':FIELDS,'ids':list(range(18,23)),'backend':'m10v_camera_library_detail','blocks':blocks,'slider8':slider8,'slider3':slider3,'table_symbol':'m10v_detail_tables','lifecycle':'stock immediate callback; cancel exits without rollback','camera_tested':False}
