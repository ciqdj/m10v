// Independent readback contract for the two owned settings controllers.
export const settingsSources=['native/gr3/m10v_film_card.c','native/gr3/m10v_film_card.h','native/gr3/m10v_film_card_data.h','native/gr3/m10v_custom_icon.rgba','scripts/generate_m10v_film_cards.py','native/gr3/m10v_settings.c','native/gr3/m10v_settings.h','native/gr3/m10v_settings_view.c','native/gr3/m10v_settings_view.h','native/gr3/m10v_settings_controller.c','native/gr3/m10v_settings_controller.h','scripts/build_gr3_settings_hooks.py'];
const need=(c,m)=>{if(!c)throw Error('independent settings: '+m);};
const movw=(r,v)=>(0xe3000000|((v&0xf000)<<4)|(r<<12)|(v&0xfff))>>>0;
const movt=(r,v)=>(movw(r,v)|0x00400000)>>>0;
const branch=(a,b,link=false)=>{const d=b-a-8;need(Number.isInteger(b)&&d%4===0&&d>=-(2**25)&&d<2**25,'branch range');return((link?0xeb000000:0xea000000)|((d>>2)&0xffffff))>>>0;};
const stockVtable=[0x5316c7e0,0x5316c774,0x5316c7bc,0x5316c740,0x5316c748,0x5316dfa8,0x5316c74c,0x5316c750,0x5316c754,0x5316c758,0x5316c760,0x5316c768,0x5316d0f0,0x5316c76c,0x5316cec8];
export function settingsPatches(m){
 if(!m.sd_library)return [];
 const d=m.settings_menu,s=m.symbols,ownerBytes=m.capture_lifecycle?.snapshot?.live_color?0x19bc:0x193c;
 need(d&&d.owner_bytes===ownerBytes&&JSON.stringify(d.private_routes)==='[33616128,33616129,33616131]'&&d.rows?.length===3,'missing route/owner contract');
 const patches=[];
 for(const [a,e,n,l] of [[0x5316f3b8,0xe300313b,'factory',false],[0x5319667c,0xe1a0c00d,'top_dtor',false],[0x5316fcf8,0xeb00ab5a,'top_ctor',true],[0x53221a4c,0xeb001c7e,'key_route',true]])patches.push({address:a,expected:e,replacement:branch(a,s['m10v_settings_controller_'+n],l),name:'settings '+n});
 patches.push({address:0x5316fcec,expected:0xe30103bc,replacement:movw(0,ownerBytes),name:'TopMenu owned tail'}, {address:0x53b36adc,expected:0x1e1d1b19,replacement:0x211d1b19,name:'Setup appended count'});
 for(let i=0;i<3;i++)patches.push({address:0x53b36bd0+i*8,expected:0,replacement:d.rows[i],name:'settings row '+i},{address:0x53b36c88+i*4,expected:0x10000000,replacement:[0x0200f100,0x0200f101,0x0200f103][i],name:'settings route '+i});
 return patches;
}
export function checkSettings(runtime,m){
 if(!m.sd_library){need(m.settings_menu===null,'unexpected menu');return;}
 settingsPatches(m);
 const d=m.settings_menu,s=m.symbols,base=m.base;
 const words=(a,list)=>{need(Number.isInteger(a)&&a%4===0&&a>=base&&a+list.length*4<=base+runtime.length,'code bounds');for(let i=0;i<list.length;i++)need(runtime.readUInt32LE(a-base+i*4)===(list[i]>>>0),'instruction at '+(a+i*4).toString(16));};
 for(const [name,old,target] of [['m10v_settings_factory_original',0xe300313b,0x5316f3b8],['m10v_settings_top_dtor_original',0xe1a0c00d,0x5319667c]]){const a=d.exports[name];words(a,[old,branch(a+4,target+4)]);}
 const vt=[...stockVtable];for(const [i,n] of [[1,'destroy'],[2,'destroy'],[7,'enter'],[9,'ready'],[10,'key']])vt[i]=s['m10v_settings_controller_'+n];words(d.vtable,vt);
 words(d.exports.m10v_settings_controller_vtable,[movw(0,d.vtable&65535),movt(0,d.vtable>>>16),0xe12fff1e]);
 for(let i=0;i<3;i++){const a=d.rows[i];words(a,[0xe92d4010,0xe1a04001,0xe1a00004,0xe3a01000,branch(a+16,0x5339de20,true),0xe1a00004,movw(1,[937,938,990][i]),0xe1a02001,0xe8bd4010,branch(a+36,0x5339dc70)]);}
 need(m.resources.texts[151]==='胶卷库'&&m.resources.texts[152]==='时间水印','root captions');
 need(JSON.stringify(m.resources.texts.slice(179,184))===JSON.stringify(['编辑：水印模式','编辑：日期格式','编辑：显示位置','编辑：文字颜色','选择胶卷']),'focus captions');
}
