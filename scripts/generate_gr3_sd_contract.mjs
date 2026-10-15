import {writeFileSync,readFileSync} from 'node:fs';
import {sdExpectedHeader} from '../node/gr3-sd-film-pack.mjs';
const file=new URL('../native/gr3/m10v_sd_contract.h',import.meta.url),expected=sdExpectedHeader();
if(process.argv.includes('--check')){if(readFileSync(file,'utf8')!==expected)throw Error('SD recipe contract is stale');}
else writeFileSync(file,expected);
