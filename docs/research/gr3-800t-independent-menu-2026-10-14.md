# GR III 2.10：800T 独立参数菜单

用户改为要求新增菜单项目、改名并保留原厂参数含义。此次在800T详细设置末尾增加ID18..22，简体caption312..316为红晕强度、扩散范围、高光阈值、红晕档位、颗粒感；其他语言用英文。其余原始参数ID、名称、记录和处理路径保持。五条旧版neutralization补丁全部撤销。早期复用滑杆文档是历史证据，不是新版操作说明。

## 原厂控制流依据

53B3488C为3组×12种列表，每个条目8B。复制整张表，仅每组kind8追加五个visibility0项目，原531AFA10对visibility0仅在拍摄设置显示。四处引用531AFA20/FA24、531AFABC/FACC、531AFFA0/FFA8、531B01F4/01F8切换到新表。53B34BD8的18项caption/hint pair保留并扩成23项。

53396670、533970A4保留原有ID≤311和language≤20范围逻辑，新增312..316查询自己的descriptor。简体language19的17个去重汉字由官方RES中的RT_CN_S字体、原厂538B51D8逐字执行查询验证为有效glyph，证据保存在builds/gr3-800t-independent-menu/evidence/glyph-proof-menu.json。glyph存在不等于实际LCD排版已验证。

四个原厂switch的default branch扩展到自定义项目：531B000C列表值、531B03F8当前值、531B05E4控件初始化、531B0BF4修改callback。范围检查只接受ID18..22且model.kind8、development0。原生531ACFEC滑杆setup分别克隆max8和max3版本；保留原closure delegate531B0FD0、manager531AC95C、invoker531ACA04，以及所有原生生命周期调用。新增12B closure分配失败保护。53390EF8会复制UTF16文本到堆，临时行值文本无悬空指针。

## 存储与拍摄

Main manager getter5320B31C，Main+4=current。四条分配size/call：5324B338/B34C、B4A4/B4B4、B5B8/B5C8、B6E0/B6E8，heap B28→B48；allocator shim保留R0结果及R4/LR，清零仅+B28..B47。Main+8..20的7个备份和+24默认cache保持B28。原厂切换/重置只memcpy B26进现有current，不交换指针；四条分配已覆盖current所有构造路径。可疑5327AC80写入是record+7A4，非Main+4。原B26文件格式及原厂setting字段不改。

私有32B block包含ready、version、checksum、No.0/No.1/No.2三组原始packed值、size32、非零footer；默认3/3/5/2/0。CAS初始化避免竞争，竞争中的捕获返回默认而不等待；稳态capture读一个atomic32B-word，不读写SD。新文件C:\M10V8CFG.BIN保存三组私有值，短读、版本/checksum/footer/字段范围异常回退默认。无SD时RAM可调。原厂timestamp ARM540BA61C..540BA6CC证明open mode1/read虚表+24及5参数ABI；成功open后必close。磁盘close/write成功不作实机保证。

531ACD24 Reset保留原532C282C调用，再仅在kind8/stage0/editmode0重置当前私有组。原厂下一条重载R0=R4，所以新增调用不破坏stock返回续接。

capture和trace从独立backend获取参数，不读原77D/77E/77F/781/784控制值。No组取current+1C0。UI gain/radius/threshold0..8，profile/grain0..3；profile映射core0/1/4/7，grain映射0/2/4/8；弱构建gain减半。原内核自然化/天空大连通源排除/绿色减弱/白灯芯保护不变。radius九档量化到五个blur pass数，非预览像素。控制record全B48纳入plane和scratch alias保护。RAW高bank保护继续有效，CFA不访问。

## 布局与验证

append49,152B，540B6000..540C2000，在原始identity executable section内。adapter540BB020（1824B），core540BB800（原3340B），诊断logger540BC800（908B），traceadapter540BCC00（2536B）；新backend540BE000，UI shim/clone540BF000起，字符串/列表540C0000起，所有块构建时拒绝重叠。trace v3记录5=私有原始packed，6=current地址，47=实际core control；原v1/v2仍可解码。

78项相关原生/ARM测试全通过（明确GR3_RTOS_PATH，无跳过）。覆盖原生selector/setup/current/callback/closure及OOM、Reset、caption新旧/越界/语言、三组state、FS重载/短读/坏checksum、原厂prefix保护、capture真backend通路且旧SI全0/全8不改变新增效果、控制record alias、核心自然化与grain、RAW及trampoline。14项800T Node tests全通过。全量Node首次116通过/1跳过/1失败，失败为并行开发的gr3-m10v-native-build.mjs当时缺失；文件出现后单独重跑该测试通过，未修改该模块。

三个固件全部独立重建回读exactExpectedPayloads，诊断audit不读取writer expectation。平台59851已重启更新；真实HTTP prepare/build200，下载标准包与本地审核包逐字节相同。证据/产物在builds/gr3-800t-independent-menu，hash/size见deliverables.json。桌面推荐诊断包800T 独立菜单版/fwdc239b.bin，机内名800T Menu，无时间戳。独立审查未发现阻塞P1/P2；真实LCD显示、SD掉电持久化与JPEG效果仍待用户实机复拍。
