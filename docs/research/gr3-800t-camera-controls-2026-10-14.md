# 800T 五项机内控制与自然化

用户确认先复用800T的现有详细设置滑杆，并提供清晰对应说明。此次只复用Bleach/tone18；原厂菜单名称不改，其他胶片保持原含义。

|原厂项|新用途|SI字节|建议显示值|
|---|---|---|---:|
|饱和度|红晕增益与亮度|77D|-1|
|色相|扩散半径|77E|-1|
|高/低调|高光阈值|77F|+1|
|高光对比|红晕档位|781|0|
|锐度|亮度颗粒|784|-4|

原厂存储值0..8显示为-4..+4。增益为raw×20（弱构建减半），自然档不再用上一版固定256增益；档位raw0关、1/2弱、3/4/5自然、6/7/8强。阈值为223+raw×3；半径通过1+(raw>>1)个二项式模糊pass改变，随输出尺寸规范化，不能把网页参考图的像素直接当作6000像素原片半径。颗粒raw0关、1..8渐强，独立于红晕档位。建议先关颗粒，之后对照试-2或0。

参考本地`gr3-film-mods/FINDINGS.md`§45–48，明确避免“菜单显示但处理阶段未应用”的既有问题；`darkslide-gr/grain_menu.py`只开放原厂Negative的粒子项，不直接套用到Bleach。此版自行在已验证的JPEG前ARM内核实现亮度颗粒，而非声称启用了原厂彩色粒子引擎。

## 完整参数通路

原厂五个滑杆的setter、记录字段和保存机制保留。`native/gr3/halation_controls.h`从拍摄ShootingInfo读值、检查范围并打包到core第二参数：bit31加bits0/4/8/12/16五个nibble；异常值默认4，异常颗粒默认0。原四参数core ABI不增加参数或改变image header。RAW地址检查仍支持已实测的高bank，不访问CFA。

`node/gr3-800t-controls.json`记录五条确切的原厂pass-through补丁。Tone18分支中的五条LDRB改为MOV4，仅中和ctx的饱和度、色相、高低调、高光对比和锐度，避免一个滑杆同时改变原色彩和新效果；对应SI五个字节不被修改。原厂函数对SI793..796的既有行为保持。对比度、阴影、暗角和清晰度继续按原规则处理。本版不提供实时取景红晕/新颗粒，也不提供机内RAW再开发红晕。

## 自然化与内存

先构建完整高光源mask，再按四邻域连通区域排除大于grid1/8的大区域，以及触边且大于16格的区域，从源头减少天空对屋顶染红。Cr<112的绿色高光不作发光源，绿色接收区域增益减至1/4；不能声称语义识别了所有树叶或只识别灯。白色灯光核心仍受保护。默认自然增益80、3passes，亮度lift为red/2，较旧实拍强档256、5passes、red×3/4收敛。

颗粒是确定性、场景相关的细微亮度噪声，正负变化近似零均值，不增添chroma噪点；纯黑/纯白不改。它不是未经验证的胶卷响应模型，也不能承诺“精确800T”。

连通队列使用打包16+16坐标，先标记visited，每格只入队一次。scratch为roundUp(6×cells,4)，最大589824字节，基址必须4字节对齐；新增未对齐scratch拒绝且无写入测试。不开红晕而只开颗粒时跳过源mask及模糊，仍保留输入和scratch验证。

尾部32KiB。生产adapter BB020（强1772/弱1776字节），core BB800..BC50C（3340字节），诊断logger BC800..BCB9C（924字节），traceadapter BCC00..BD5AC（2476字节）。全部无重叠，原厂startup identity executable mapping核验覆盖至BE000。trace wrapper BL为EB0006FC；trace版本2在第47word记录实际参数，旧版本1仍可解码。

## 交付与验证

|产物|字节|SHA256|
|---|---:|---|
|常规强版|31172536|`5403d92c06231212cb7c562d59456073de6c6c787471cbbad7a64b83f8eea48f`|
|常规强版＋时间戳|31273724|`71447e5ee65e50a39328da84033778d4f9498eb5ab1aa9a9cec5af618d30f4fc`|
|800T Tune诊断版|31172536|`dfbeacf64bfd65e53b19cdbad586ec657f8173ff51d3b524d886d89b25d4157b`|

构建和审计保存在`builds/gr3-800t-tunable`；桌面交付`800T Tune/fwdc239b.bin`及`机内调节说明.md`。诊断版无时间戳。独立审计从可信模板、原生代码锁和固定logger/traceadapter机器码重建所有section，不读取writer expectation。泛用审计兼容历史24KiB和当前32KiB尾部；当前accepted prepared仍必须32KiB且与独立预期逐字节绑定，没有放宽当前导出证明。

63项相关原生/ARM测试通过，覆盖sky、绿色源、五个参数变化、gain0仍可grain、chroma/边界/黑白保护、奇数grid对齐、host/ARM一致、trace参数记录、实际桥接、高RAW bank与原厂参数pass-through。先执行旧版观察五项新行为测试失败，以及stock pass-through输出8而非中和4；再验证新实现。独立审查修复了未对齐scratch问题，未发现其余阻塞P1/P2。

全量Node129项：128通过、1跳过、0失败。完整Python87项：85通过、2个已有首页断言失败：`tests.test_workflow.WorkflowTests.test_direct_file_open_keeps_styling_and_explains_server_requirement`、`tests.test_workflow.WorkflowTests.test_page_exposes_actual_import_backup_and_locked_features`。初次运行出现原厂源文件改名期间的缺文件，以及并行旧film-bay实现/测试过渡状态；源路径稳定、当前800T历史审计兼容和新版文案修正后重新执行，上述临时错误已消除，未修改无关film-bay逻辑。

服务在59851重启；真实HTTP预检→构建→下载返回200，31172536字节、SHA5403d92c…，与常规候选一致。DNG独立rawpy开发和近似film表驱动的native参考图已查看：窗灯有温和红边、无连续屋顶红描边；它不是相机ISP或新固件实拍预测，不能作为硬件验证。

**旧版红晕已由00003971实拍和stage100确认；新五项控制、自然化及颗粒的实机表现仍需复拍。** 建议用上述初始值拍带窗灯RAW+JPEG，再只提高饱和度对照。新M10V8.BIN能核验五个实际值、core返回和前后采样；采样总和不能取代全图或CFA完整性证明。
