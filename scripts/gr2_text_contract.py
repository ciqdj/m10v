"""Extract exact stock text pointer preimages; never import GR III addresses."""
import struct
from scripts.analyze_unity_update import official_profile
from scripts.analyze_unity_runtime import parse_executable_load_map
IDS=(112,113,114,115,126,110,111)
SLOTS=(0,1,1,2,3,4,4)

def effect_name_contract(code:bytes)->dict:
    official_profile(code,'gr2');segments=parse_executable_load_map(code)[:15]
    def word(address):
        for row in segments:
            if row['address']<=address and address+4<=row['address']+row['length']:
                return struct.unpack_from('>I',code,row['source_file_offset']+address-row['address'])[0]
        raise ValueError('GR II text contract outside loaded component')
    directory=word(0xa03a4c20)
    if directory!=0xa05909ec:raise ValueError('GR II stock text directory changed')
    rows=[word(directory+4*i) for i in range(21)]
    expected=[[word(row+4*(identity-1)) for identity in IDS] for row in rows]
    return dict(directory_word=0xa03a4c20,directory=directory,rows=rows,ids=list(IDS),slots=list(SLOTS),expected=expected)

def contract_header(contract:dict)->str:
    def words(values):return ','.join(f'0x{value:08x}u' for value in values)
    return '\n'.join((
        '/* Generated from the exact identity-locked GR II component. */',
        f'#define GR2_TEXT_DIRECTORY_WORD 0x{contract["directory_word"]:08x}u',
        f'#define GR2_TEXT_DIRECTORY 0x{contract["directory"]:08x}u',
        'static const uint32_t gr2_text_rows[21]={'+words(contract['rows'])+'};',
        'static const uint16_t gr2_name_ids[7]={'+','.join(map(str,contract['ids']))+'};',
        'static const uint8_t gr2_name_slots[7]={'+','.join(map(str,contract['slots']))+'};',
        'static const uint32_t gr2_name_preimages[21][7]={'+','.join('{'+words(row)+'}' for row in contract['expected'])+'};',''))
