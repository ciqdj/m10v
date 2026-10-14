// Stable IDs and every documented v13/v16 consumer value for GR III 2.10.
// A candidate must not be exported until these mappings are wired to all callers
// and independent per-film settings are stored by the camera.
const slots=[1,2,3,4,5,7];
const icons=[0x05,0x06,0x07,0x1d,0x2d,0x2e];
const need=(condition,message)=>{if(!condition)throw new Error(message);};

export function filmToneMap(films){
  need(Array.isArray(films)&&films.length>=1&&films.length<=6,'新增胶片数量必须为1至6');
  const seen=new Set();
  return films.map((film,index)=>{
    need(film&&typeof film==='object'&&!Array.isArray(film)&&
      typeof film.id==='string'&&/^[a-z][a-z0-9-]{0,30}$/.test(film.id),
      '新增胶片稳定ID无效');
    need(!seen.has(film.id),'新增胶片ID重复');seen.add(film.id);
    return Object.freeze({id:film.id,index,tone:25+index,menuIndex:12+index,
      rawEnum:13+index,imageTone:0x10c+index,recordSlot:slots[index],
      stringId:0x380+index,iconId:icons[index]});
  });
}

export function stockSafeTone(tone,map){
  need(Number.isInteger(tone)&&tone>=0&&tone<=255,'胶片模式编号无效');
  need(Array.isArray(map),'胶片映射无效');
  if(tone>=11&&tone<=22)return tone;
  return map.some(entry=>entry.tone===tone)?tone:11;
}

export function privateFilmToneFromRawEnum(value,map){
  need(Number.isInteger(value)&&value>=0&&value<=255&&Array.isArray(map),'RAW显影编号无效');
  const entry=map.find(item=>item.rawEnum===value);
  return entry?.tone??null;
}
