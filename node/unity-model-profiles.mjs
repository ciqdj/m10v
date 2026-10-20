// Facts proved against the two supplied official images; no writable runtime addresses.
function freeze(value){if(value&&typeof value==='object'){Object.values(value).forEach(freeze);Object.freeze(value);}return value;}
export const unityProfiles=freeze({
  gr2:{model:'GR II',filename:'rg2_v003.frm',size:14033920,version:0x0300,public_version:'3.00',nested:'rg2_v001up',
    sha256:'3643850f2ae74ae967eb336794048f554caa1b11d05b8569824d5719f1838331',
    components:{
      b01firm6:{size:7896704,sha256:'9e0d291f5b9b74f76a2dd269c4b23fe8f524b5db92b86bf82150d5dc3096abf8'},
      b01firm8:{size:6132308,sha256:'13fa830bff194679628eb1bb3f233420ee23c4fca3a28c4b650c53692820de95'},
    },resources:{table:0x786000,count:121}},
  gr1:{model:'GR',filename:'rg1_v051.frm',size:12471808,version:0x0501,public_version:'5.01',nested:'rg1_v001up',
    sha256:'12b503a831d58d031500e24518624d89dcdec965eae52d7699b73040084f38ca',
    components:{
      b01firm6:{size:6643200,sha256:'9c0cea5c6474ce0969b5be5d574e1d6d98accd6e8a0d77e2b7fe773e968443fd'},
      b01firm8:{size:5824084,sha256:'08c19e07fafb12e075e1e5cc4f74fe22a1b57132614a4e8d4174c669a865e728'},
    },resources:{table:0x654000,count:119}},
});
