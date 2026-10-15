import {buildSdFilmPack,auditSdFilmPack,sdCrc} from "./gr3-sd-film-pack.mjs";
function encodeZip(rows) {
  const local = [];
  const central = [];
  let offset = 0;
  for (const name of Object.keys(rows)) {
    const bytes = rows[name];
    const filename = Buffer.from(name);
    const checksum = sdCrc(bytes);
    const header = Buffer.alloc(30);
    header.writeUInt32LE(0x04034b50);
    header.writeUInt16LE(20, 4);
    header.writeUInt16LE(0x800, 6);
    header.writeUInt32LE(checksum, 14);
    header.writeUInt32LE(bytes.length, 18);
    header.writeUInt32LE(bytes.length, 22);
    header.writeUInt16LE(filename.length, 26);
    local.push(header, filename, bytes);
    const record = Buffer.alloc(46);
    record.writeUInt32LE(0x02014b50);
    record.writeUInt16LE(0x0314, 4);
    record.writeUInt16LE(20, 6);
    record.writeUInt16LE(0x800, 8);
    record.writeUInt32LE(checksum, 16);
    record.writeUInt32LE(bytes.length, 20);
    record.writeUInt32LE(bytes.length, 24);
    record.writeUInt16LE(filename.length, 28);
    record.writeUInt32LE((0o100644 << 16) >>> 0, 38);
    record.writeUInt32LE(offset, 42);
    central.push(record, filename);
    offset += header.length + filename.length + bytes.length;
  }
  const centralSize = central.reduce((size, part) => size + part.length, 0);
  const ending = Buffer.alloc(22);
  ending.writeUInt32LE(0x06054b50);
  ending.writeUInt16LE(Object.keys(rows).length, 8);
  ending.writeUInt16LE(Object.keys(rows).length, 10);
  ending.writeUInt32LE(centralSize, 12);
  ending.writeUInt32LE(offset, 16);
  return Buffer.concat([...local, ...central, ending]);
}

export function exportSdFilms(input){
 if(!input||typeof input!=='object'||Array.isArray(input)||!Object.hasOwn(input,'ids')||Object.keys(input).some(k=>!['ids','model'].includes(k))||(input.model!==undefined&&input.model!=='gr3'))throw Error('请选择 GR III 胶卷');
 const pack=buildSdFilmPack(input.ids),receipt=auditSdFilmPack(pack);
 const instructions='M10V SD 胶卷库 / GR III 2.10\n'+
 '需要配套的 M10V SD 胶卷库固件；旧内置胶卷库固件不读取此文件，GR IIIx 暂不支持。\n'+
 '解压，将 SD/M10V 目录复制到 SD 卡根目录，与 DCIM 并列。更新时只替换 FILMS.M10，保留其他文件。\n'+
 '机内：MENU > Image Control > M10V Library > Choose Slot，选择要替换的槽位；返回后进入 SD Film Library。\n'+
 'Previous page / Next page 翻页，选卷按 OK 装入。Back 返回，Done 退出。最多五个活动槽，卡上可存全部当前平台胶卷。\n'+
 '装入成功后重启或换卡仍保留。无卡、损坏或不兼容文件不替换原槽。失败提示后请保留原配置重试。\n'+
 '文件包含完整配方和图标；当前运行时只接受与其支持版本完全匹配的 33 款，未来新配方需匹配固件。\n'+
 '离线验证候选，尚未通过真机 SD 换卷验收。成像范围沿用现有静态 JPEG 引擎。\n';
 return {receipt,zip:encodeZip({'SD/M10V/FILMS.M10':pack,'README.txt':Buffer.from(instructions),'manifest.json':Buffer.from(JSON.stringify(receipt,null,2)+'\n')})};
}
