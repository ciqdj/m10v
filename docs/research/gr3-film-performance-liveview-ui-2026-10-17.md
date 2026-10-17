# GR III 胶卷保存性能、取景与参数页（2026-10-17）

## 本轮输入与范围

用户回报上一候选胶卷成片确实有效，另反馈连拍堆叠、保存数秒、取景仍是原厂槽位色彩、FN参数页乱码与重复图标。用户随后确认驱动模式为间隔合成，明确要求忽略连拍问题。本轮不修改驱动模式、HDR抓拍调度或中止逻辑。

上传固件SHA256：`3e09d37ef824f5d850c3143aef73a26eae1cab4d5a5a4cf98bb54b9a20fb7edf`，与上一轮交付完全一致。四页日志CRC有效，build ID为`dd41748d`。尾窗包含5207与蓝凤凰的6000×4000处理，以及间隔合成中sequence_mode=2、无JPEG请求的安全拒绝；不能把这些拒绝当作连拍根因。最后一条before也不能单独证明崩溃。

## 已定位与修复

### 保存性能

1. 旧调试版每次日志事件都会分配8192字节、读两个4096字节页、验证记录、写对侧4096字节页。拍摄路径有十余个事件；800T还额外扫描24MP全图，仅为event114的高光统计。
2. 当前移除该额外全图统计，保留8×8 CPU像素采样。拍摄trace由调用栈持有，最多16条；render前一次flush、完成后一次flush，正常pre最多10条/post3条。拒绝路径一个批次。保留render前快照，处理停滞仍有定位依据。
3. `m10v_debug_batch`同一channel最多16条共享一个SD事务，继续先读双页、只写另一页、CRC与原63槽环结构不变。单事件API包装此函数，菜单日志语义不变；重入或并发写入仍跳过，不窃取或清除其他writer所有权。
4. 日常版关闭全部调试写入，另提供保留上述批日志的诊断版。
5. 红晕近场三抽头沿distance lane滚动复用，`energy_pixel`调用从每行`3w`降为`w+2distance`，不新增scratch、不改公式、阈值、核或品质。
6. 5207与哈曼LUT使用相同四顶点的标量权重代数重排，排序、clamp与`+127/255`舍入保持不变，去掉每像素数组和嵌套循环。

离线证据（不是相机保存秒数）：

| 项目 | 原版→优化版 |
| --- | --- |
| 24MP host -O2，800T halo4 | 272.4→132.8ms |
| 24MP host -O2，halo4+soft3 | 296.1→154.5ms |
| 24MP host -Os，5207完整render | 423.3→305.5ms |
| 24MP host -Os，蓝凤凰完整render | 435.0→304.7ms |
| 24MP host -Os，RED完整render | 441.5→305.6ms |
| ARM -Os，256 RGB样本，5207 LUT | 73984→27991指令（减少62.2%） |
| ARM -Os，256 RGB样本，哈曼四表各自 | 76288→31063指令（减少59.3%） |

五张表的全部256³ RGB输入（83,886,080组）逐字节一致。红晕完整输出在2×1至6000×4000、不同强度/柔光/范围/阈值及padding/scratch哨兵下与旧算法逐字节一致。此优化保持算法结果，无法据host/ARM指令数保证实机具体秒数或等于原厂ISP速度。

### 取景

用户允许无法实时胶卷模拟时显示原色。本轮选择将五个胶卷承载槽的LiveView色彩参数中和为Standard，不实现软件胶卷逐帧处理。

四个共享helper仅在原厂Still vtable `53dbd8a0`或LiveView vtable `53dbd938`下，将局部tone12/18/19/20/21作为11分派；静态处理计划的caller门禁保留。原SI tone与LiveView对象`+1a8`的dirty缓存身份不改。非承载模式与其他对象不归一化。

正式测试执行真实LiveMake `536ddecc`，在stage1元数据形状下，五槽×默认/非默认两组的输出均与官方Standard逐字节一致，仅允许SI tone与对象身份缓存差异。实际stage0需要`CorrectWaveDetectData`的机身黑电平/AWB标定：`536de1bc→536e9bd8→536e9558→536c2a30`；未伪造这些标定数据或跳过该色彩计算来声称完整硬件预览已通过。stage0共享helper门禁及寄存器另有显式服务边界测试。真实LCD仍待验收。

### FN参数页

- 原厂`5339e2f8→53390ef8`接收ASCII，经strlen及byte→UTF16转换。旧代码传UTF16，因此数字只剩首字符、中文变为低字节乱码。
- 所有私有行固定使用原厂饱和度图标`0x1e3`，导致相同三圆图标。`r1=0`为已确认的原厂隐藏图标分支。
- 原厂text widget仅40px宽，短参数名仍会截断。新增`531b0008`窄dispatch通过原厂`View::setBounds(533ab548→533ad318)`扩展私有行至120px，原厂行复用时恢复40px。复制原厂18个handler表，并恢复寄存器与CMP条件码。

当前行显示`Gain3/8`、`GrnLow`、`PosLeft`等短名称和值，完整中文标题保持原厂caption资源；轨道资源57/560已检查原始像素，继续使用原厂轨道。26项ARM测试覆盖全部11字段经真实setter转换、图标隐藏、实际layout bounds/local drawing rect、复用恢复与原厂18分派。没有用字符串存在代替真实调用链验证，也未把离线API状态等同LCD截图验收。

## 构建与验收

性能代码改变完整renderer源契约，已重新生成SD合同；需随固件复制配套的新`M10V/FILMS.M10`，内部五槽journal保持兼容。两个固件都保留画幅、水平仪、负片颗粒，RAW像素区及原有内存守卫不放宽。

完整测试、最终BIN回读、哈希和独立代码审查结果随交付证据保存。未刷机、推送或部署；用户须验收新取景、参数页可读性与实际保存耗时。


补充参数布局检查：原厂`533ad318`已有bounds/local drawing rect相等判断，相同尺寸直接返回。真实ARM序列private/private/stock/stock/private/private只在三次实际尺寸变化时触发invalidate，不会因每次row dispatch重复设同一bounds而形成持续重绘。字体scale32×32已确认，当前字符串最多7字符；实际字形advance依赖机身字体服务，未拿假定字宽充当LCD像素验证。

成品信息：日常版SHA256 `49eba1edb0958571fc3b72a7d971db8c7420b410a40f6f384866f0ac38276913`；诊断版SHA256 `ef4339c2b2b16b8bbbb47370bd39fc6f61794219d26bce5ad413498c42567aaa`，build ID `addc4f0c`。两版配套36卷包SHA256 `1fa7f8d145e517d2cb1e4a821e06323902ccb98150d27cf904efda1908ba3e77`。

从最终BIN解包：日常/诊断各5项ISP回归通过，诊断2项五卷CPU像素处理和拒绝守卫通过；画幅/水平仪扩展区与上传固件逐字节相同。独立代码审查未发现阻止候选交付的问题。

验证启动方式：首次`unittest discover -s tests`把tests目录作为顶层，`test_api`和`test_backup`的包内相对导入报错；已停止该次运行，改为`.venv/bin/python -m unittest discover -s tests -t .`完整重跑。早期LUT子任务使用系统Python曾因缺colour导致参考测试出错，切换项目.venv后75项相关回归通过，没有修改依赖。最终验收以正确解释器/包根目录的全量结果为准。

最终完整回归：`.venv/bin/python -m unittest discover -s tests -t .` 404项，908.660秒，OK（5跳过、1预期失败）；预期失败为旧实拍故障固件的`test_known_flashed_bug_library_targets_highlighted_slot`复现，修复固件对应测试通过。`npm test -- --test-concurrency=1` 208项，204通过、4参考样本缺失跳过、0失败，696.946秒。最终变更无新增失败，SD合同及changelog门禁、git diff --check均通过。
