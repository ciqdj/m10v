# GR III 捕获生命周期：RAW 指针、保存回调与等待边界

日期：2026-10-18。锁定 GR III 2.10 RTOS，SHA256 `8a4eafcad2716e0b21e9909264e1242e534f0e39e05cba82a53546ceb4070b67`，VA 基址 `0x53000000`。只读原厂镜像和现有 adapter；未修改生产固件。下列静态链和小函数 ARM 执行均不是实机验证，未运行 ISP、JPEG 硬件、SD 控制器或原厂调度器。

当前证据不能把第 3 张后黑屏归因到某个固定 20/30/40 秒原厂超时，也不能把一次 `RAW source=0` 认定为丢片或分配失败。原厂确有正常清零和所有权转移路径；JPEG 提交后的局部等待及找到的同步保存等待均传入无限等待 `-1`。持续占用编码前 worker 会延迟回调和后续清理，可能增加排队及内存压力；具体队列深度、同时在途张数和最终文件完成仍需实机日志。

## 复现

```sh
.venv/bin/python scripts/analyze_gr3_capture_lifetime.py --probe-original
.venv/bin/python -m unittest tests.test_gr3_capture_lifetime -v
```

输出到忽略目录 `builds/gr3-isp-research/lifetime/`：逐地址 `.asm`、`manifest.json`、`original-arm-probes.json`。脚本先拒绝不匹配 SHA 的镜像；没有隐式下载或修改输入。`--address 0x... --count N` 可扩展静态窗口。线性反汇编会把 switch table 的数据解释成 ARM 指令，table 必须按小端 word/间接跳转判读，不能据伪指令推断控制流。指针引用和 BL 扫描是 aligned ARM 搜索，不是全程序引用证明。

本环境 Unicorn 在沙箱内可能 SIGILL，因此上述含 ARM 执行的命令使用了提升权限；不是靠绕过断言继续。每个 probe 有指令上限，必须返回 sentinel；仅 OS/assert/event 边界被截获。两项 unittest 均通过；具体涵盖 2 个 setter、12 个保存状态、6 个 event wait 输入组合。

## R+60 的四种来源不能混淆

原厂 `BEStillRecipe` vptr 为 `0x53d0fc90`。vtable `+0x70`，即表项 `0x53d0fd00`，指向 `0x5350d7e8`。这是一组 buffer setter，不是独立 free 函数。

入口 `0x5350d7e8` 先把 r1 减 1；id=1 对应 table `0x5350d810` -> `0x5350d878`：

- r0=recipe，r1=buffer id，r2=backing 输入。
- r2=0：`0x5350d87c` 清 R+2f4；`0x5350d880` 清 R+60；直接返回。
- r2 非零：`0x5350d890` 存 R+2f4；取 R+252 的 u16，按 `backing + headerRows*128`，再向上 64 字节对齐，`0x5350d8b8` 存 R+60，`0x5350d8c0` 同时存 R+44d0。该快速分支要求 vtable+ac 等于 `0x5350d614`；其他类走虚方法。
- 它不返回 success/error enum：零分支 r0 仍为 recipe；快速非零分支 r0 已成为 aligned source。不能按 r0=0/非零判断 setter 成败。

原始 ARM 小执行以 recipe=60000000、headerRows=2 验证：输入 0 后两个字段都为 0；输入 70000000 后 backing=70000000、source=70000100。没有调用 allocator，也没有任何硬件调用。

### 确认的合法所有权转移

`0x53518238` 在 `0x53522e84` 对 owner+5ac 列表计数返回 1 时走 `0x535182c8`。该计数函数是按对象虚方法 +30/+28/+2c 的状态筛选统计，不应直接命名为“队列总深度”。取出的目标 recipe=r4、当前 recipe=r7。在普通 stock getter 分支中：

1. `0x535182f8` 先清理目标 id1 的旧 allocation。
2. `0x5351831c..28` 把当前 R+2f4 经目标 setter(id1,backing)交给目标。
3. `0x53518344..48` 把当前 R+60 直接复制到目标 R+60（保留实际 source/crop）。该快速分支要求 getter vtable+84 为 `0x5350d488`。
4. `0x5351834c..5c` 调当前 recipe 的 setter(id1,0)，清掉当前 R+2f4/R+60。

这条静态链足以证明“source=0 不蕴含 allocator failure”。它不证明用户那一次 guard12 就来自此路径；还需要 setter 的 LR、recipe 地址及目标关联。也不能据此取消 adapter 的 RAW 保护门：若当前 hook 看到空 source，尚无可证明的 CFA 保护区间，跳过仍是合理的 fail-closed 行为。

### 分配失败也可能产生同样的零

`0x535216d0` 是按 buffer id 分配的辅助路径。普通分支 `0x53521858` 获取请求 size；`0x53521878` 调 `0x536a27e8`，返回值存 r5；`0x53521894` 调 recipe setter(id,r5)；`0x53521898..a0` 把非零转 true，零转 false。因此 id1 分配返回零时，也可能写出完全相同的 R+60=0。

底层 `0x536a26f0` 通过 `0x536a259c` 查询可用量，`0x536a2784..8c` 当 available <= requested 直接返回零；足够时才经池对象 vtable+8 分配。`0x536a27e8` 按 policy 选择池或回退；本次未证明任意池的容量、单位或最坏碎片行为。source=0、malloc失败和 free memory 不足应各自记录，不能互相替代。

另 `0x53521398..d8` 批量分配循环也会把返回值交 setter；分配零时该循环返回 0。`0x53521470` 的替换分配在返回零时直接失败，不写 setter，证明“分配失败必清原 source”同样不成立。

### 正常释放

单 buffer 清理 `0x53521d14`：id1 table `0x53521d58` -> `0x53521dc4`，先查 recipe vtable+54 的保护状态；非零则跳过。无保护且 backing 非零时，`0x53521e14` 调 `0x536a248c` 释放 backing，`0x53521e58..68` 再 setter(id,0)。

必须区分“先释放后清零”和上述“转移后清零”：仅观察最终 source 值区分不了。应记录 setter 入口 LR、buffer id、backing old/new 和 recipe，必要时关联 `0x536a248c` 的释放记录。不要在此处解引用即将释放的像素区。

## adapter 阻塞对应哪个等待

当前 hook 在 `0x535048e8` 原厂 JPEG 服务提交之前。原厂 handler `0x535047d4` 在提交后才到 `0x53504944` 等待自己的 event：r0=module+34，r1=2，r2=0，r3=从 `0x53d5edcc` 取出的 `0xffffffff`。

`0x536a9e8c` 的字符串是 `WaitOr`：

- 正数 timeout 原样传到 kernel facade `0x530512a8` 的第 5 参数。
- 0 仍传 0；负数转 -1。不能把 -1 解读为 1 ms。
- kernel 返回 0 时 wrapper 返回 bool 1；`E_TMOUT = -0x320000 = 0xffce0000` 时返回 0。日志断言字符串 `0x53d5c0c0` 为 `(err == E_OK) || (err == E_TMOUT)`；其他错误走断言，不能假设正常恢复。
- wrapper 的 bool 不是 kernel 的数值 error code。`0x53504944` 后原厂代码未检查该 bool，而继续处理输出；但此处参数为无限等待。

有界 ARM probe 对 timeout=0、25、-1 分别注入 E_OK/E_TMOUT，确认 stacked timeout 和 bool 映射；这只证明参数/返回语义，不证明实际 RTOS 如何调度或何时送达事件。

所以 adapter 的 20–40 秒并不消耗这个尚未开始的局部 wait 截止期。其他线程可以有自身期限；本报告没有证明不存在全局 watchdog、UI/电源等待或 SD 超时。

## 保存返回：应读结果字节，不能读回调 r0

`WriteStillFile` 字符串 `0x53c5eb04` 由 `0x534eb8b4` 引用；函数准备 image-write info 后 `0x534eba44` 调同步桥 `0x534ecb3c`。后者先发服务虚调用，再在 `0x534ecb88` 等 event bit2，timeout 同为 -1，清 event 后 `0x534ecb98` 返回 obj+10 的 u8。这是服务完成结果，未证明文件系统已持久化到介质。

该桥对象构造 `0x534eca58` 将 obj+10 初始化 0，vptr=53c5ed78；vtable+8 回调为 `0x534ec9b8`。确认的回调协议：

| callback r1 opcode | event bit | payload r2+4=0 | status 1/2 | status >2 |
|---|---:|---:|---:|---|
|41000|1|obj+10=1|obj+10=0|保留原值|
|42000|2|obj+10=1|obj+10=0|保留原值|
|43000|4|obj+10=1|obj+10=0|保留原值|

这三种 opcode 都会 signal 对应 bit，然后 callback 的 r0=0，无论成功/失败。`status >2` 不是已解明的失败枚举；原厂分支会保留结果字节，本次以初值7f执行确认。普通构造初值0，但不能把未知状态硬解释为某个命名错误。未知 opcode 走另外的过滤路径，也不能沿用表格。

`0x534eb8b4` 将同步桥的 byte 返回值保存在 r4，经对象清理后 `0x534eba7c` 返回。上层 `0x534e8828` 调用后取 r0，在 `0x534e8838` 判断是否零。建议实机最少记录该桥的 enter/exit、callback opcode/status、返回 byte、用户文件标识关联；目前既有 adapter 退出日志不覆盖它们。

这条 StillWrite 链与现有 JPEG macroprocess 的 buffer 清理之间的全程对象关联尚未闭合，因此不能仅按函数名断言某个 callback 对应用户的第 N 张 RAW 或 JPEG。物理写卡完成和目录可见性还需要存储服务层/实机文件核验。

## 调度器确有资源等待路径，但不是已证明的 30 秒超时

`0x5351ea9c` 为 module 配置与发消息。通用 module receiver `0x53505c8c` 在 `0x53505d78` 调具体 handler；直到 handler 返回，才经 `0x53505e28` 调 owner 回调。因此长时间同步 adapter 延迟 owner 完成通知。既有 contract 所述 planner kind10 等待和后续 cleanup 顺序仍成立；延迟的数量级对吞吐和在途 buffer 有直接意义，但不自动证明数据损坏。

scheduler `0x5351fc6c` 的 kind2 分配路径 `0x5351feb4` 调 `0x535216d0`，false 走 `0x5352013c`。这里有全局 `0x552d08d8` 的计数；`0x5352015c..6c` 自增后比较 `0x3e8=1000`，大于时 `0x53520194..b0` 清计数并重新进入当前 entry。它是循环/重试计数，**没有读取 clock**，不能称为1000ms或固定秒数超时。尚未证明每一轮对应多少 RTOS tick、系统负荷或可重入行为。`0x53520260` 还会检查 owner 队列状态并进入断言/诊断路径，这一轮没有把所有状态的运行语义命名。

没有得到“3 张”固定队列容量，也没有证明 20–40s 一定超过某个 stock 截止期。需要记录队列筛选计数、当前 sequence entry kind/id、allocation size/result、重试计数并与 wall-clock tick 同时关联。

## 下一版安全调试候选（未实施）

|边界|最小数据|能回答的问题|
|---|---|---|
|setter 5350d7e8 入口/5350d878|recipe,id,r2,LR,old+2f4,old+60|分配、转移、释放哪一种清零|
|transfer 53518344/5351835c|src recipe,dst recipe,source/backing|是否把 RAW 所有权交给下一 recipe|
|allocation 53521878 后/535216d0 返回|recipe,id,size,policy,result|是否真实分配失败，是否反复重试|
|JPEG submit 535048e8 前/后及53504944后|recipe,module,event,return,tick|adapter完成、队列提交与编码回调是否各自完成|
|保存回调534ec9b8/同步返回534ecb98|object,opcode,payload status,result,tick|服务成功、失败、未回调还是仍在等待|
|normal free 53521e14及setter清零|recipe,id,backing,LR,tick|是否释放过早、重复释放或正常回收|

这些地址是**离线候选**，不是可以直接打补丁的安全认证。每处需要原始寄存器/CPSR、stack/ABI、覆盖指令和 trampoline 校验。使用有容量限制的内存 ring，记录单调 tick 和递增关联号，不保留像素指针、不读像素、不在 buffer/allocator/event 回调热路径同步写 SD，不新增等待或调用未证明可重入的全局服务。只在已有安全日志边界批量冲刷；掉电前 ring 丢失仍可能。确认模块/保存对象能映射同一拍摄关联号后，才能将四个 adapter profile 与最终 RAW/JPEG 文件一一对应。
