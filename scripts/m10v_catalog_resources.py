"""M10V native labels; synchronized with the GR3 camera resource inventory."""
import re,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def catalog_texts(sd_library=True):
    names = re.findall(r'\{"([^"\n]+)",[-0-9]', (ROOT / 'native/gr3/m10v_library.c').read_text())
    if len(names) != 33 or len(set(names)) != 33: raise ValueError('original catalog names incomplete')
    texts = names[:32] + [f'M10V Slot {i}' for i in range(1, 6)] + [
        'M10V Film Library', 'Save failed. Try again.', 'M10V Library',
        'Choose Film', '颗粒', '柔光', 'Timestamp', 'Choose Slot',
        'Grain Off', 'Grain Weak', 'Grain Medium', 'Grain Strong',
        'Diffusion Off', 'Diffusion Weak', 'Diffusion Medium', 'Diffusion Strong',
        'Timestamp Off', 'Date Only', 'Date and Time', 'Date Format', 'Stamp Corner', 'Stamp Color', 'Back',
        'YYYY.MM.DD', 'DD.MM.YYYY', 'YYYY-MM-DD', 'YY.MM.DD',
        'Top Left', 'Top Right', 'Bottom Left', 'Bottom Right',
        'White', 'Orange', 'Red', 'Yellow', 'Back', 'Done', names[32],
        '800T Halation','光晕强度','扩散范围','高光阈值','Halation Profile',
        *[str(i) for i in range(9)],'Off','Weak','Natural','Strong',
        *[f['name'] for f in json.loads((ROOT/'web/gr3/film-catalog.json').read_text())['looks']], '5207','Light Leak','Grain Size','Leak Gain','Leak Position','Leak Spread','Leak Variation','Fine','Standard','Coarse','Left','Right','Top','Bottom','Corner','Random','Fixed','Per Shot','Reset Texture','Phoenix II','HARMAN RED','Phoenix II Halation','RED Exposure','EI 125','EI 64','EI 250']
    if len(texts) != 151: raise ValueError('private resource inventory differs')
    if sd_library:
        translations={'M10V Film Library':'胶卷库','Save failed. Try again.':'读取或保存失败，请检查存储卡','M10V Library':'胶卷设置',
            'Choose Film':'内置胶卷','Timestamp':'时间戳','Choose Slot':'设置槽位',
            'Grain Off':'颗粒关闭','Grain Weak':'颗粒弱','Grain Medium':'颗粒中','Grain Strong':'颗粒强',
            'Diffusion Off':'柔光关闭','Diffusion Weak':'柔光弱','Diffusion Medium':'柔光中','Diffusion Strong':'柔光强',
            'Timestamp Off':'时间戳关闭','Date Only':'仅日期','Date and Time':'日期和时间','Date Format':'日期格式',
            'Stamp Corner':'显示位置','Stamp Color':'文字颜色','Back':'返回','Done':'完成','Top Left':'左上','Top Right':'右上',
            'Bottom Left':'左下','Bottom Right':'右下','White':'白色','Orange':'橙色','Red':'红色','Yellow':'黄色',
            '800T Halation':'800T 光晕','Halation Profile':'光晕模式','Light Leak':'漏光','Grain Size':'颗粒尺寸','Leak Gain':'漏光强度','Leak Position':'漏光位置','Leak Spread':'漏光范围','Leak Variation':'漏光变化','Fine':'细','Standard':'标准','Coarse':'粗','Left':'左','Right':'右','Top':'上','Bottom':'下','Corner':'角落','Random':'随机','Fixed':'固定','Per Shot':'每张变化','Reset Texture':'重置质感','Phoenix II':'蓝凤凰','Phoenix II Halation':'蓝凤凰光晕','RED Exposure':'RED 曝光','Off':'关闭','Weak':'弱','Natural':'自然','Strong':'强'}
        texts=[translations.get(t,t) for t in texts]
    if sd_library:
        texts += ['胶卷库','时间水印','左右选择 OK更换 MENU返回','左右选卷 上下翻页 OK安装 MENU返回','上下选择 OK设置 MENU返回','左右调整 OK保存 MENU取消','存储卡中没有可用胶卷','胶卷库已变化，请重新选择','保存失败，请检查存储卡','水印模式','日期格式','显示位置','文字颜色','关闭','仅日期','日期和时间','YYYY.MM.DD','DD.MM.YYYY','YYYY-MM-DD','YY.MM.DD','左上','右上','左下','右下','白色','橙色','红色','黄色','编辑：水印模式','编辑：日期格式','编辑：显示位置','编辑：文字颜色','选择胶卷']
    texts += ['Portra 160','富士业务用 100','乐凯 C200','CCD Classic']
    return texts
