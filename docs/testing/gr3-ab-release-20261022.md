# GR III A/B 发布集成 · 2026-10-22

用户对 `gr3-ab-no-live-ui-20261021` 明确反馈“完美，合入 master 并推送 github和宝塔”。仓库正式分支为 `main`，同步 `develop`；验收与授权记录在 `gr3-ab-user-acceptance-20261022.json`。验收 BIN SHA256 `d6709de38d5283321b8ab23fad80bf1f83bbd1c9433faf27ff75c248d435ee0b`，ZIP `e735004db3b5447f3732c7072da9f350e1d071e7546c0c228e0c5dae62ca85d8`。

## 集成范围

在干净的现有独立 worktree 从 `origin/main=a895cda0e347a33c0a2db04a8cfa615dcd939161` 创建发布分支。没有改动共享脏工作区、覆盖其他迭代或上传固件/日志/照片。GR III 2.10 的四个 runtime 文件与验收包源指纹完全相同：

- `native/gr3/m10v_ab.h`：保留44字节 ABI，废弃控件指针改为保留字段。
- `native/gr3/m10v_ab_camera.inc`：完整移除 A/B 取景文字控件及创建/挂载/隐藏/析构，移除转换与普通影像控制 OK 的同步日志；MENU/ADJ 仍交原厂。
- `scripts/build_gr3_settings_hooks.py`、`node/gr3-settings-menu.mjs`：生成并独立核验 `live_ui:false`。

另合入相应 ARM 守卫、原厂文字树验证、最终 BIN 回放、候选构建脚本与操作说明。更新日志 `2026.10.22.1` 与使用说明同步说明 DISP 配对/快切/停用操作。

## 保留线上首张修复

上一独立 A/B 包冻结了较早成像基线，而线上 main 已在另一迭代发布并验收本张 recipe 提交前冻结修复。因此本次不是用独立快照覆盖 main：其余120个 runtime 来源与 main 一致；相对独立 A/B 包只有 `m10v_isp_recipe_color.c`、`build_gr3_isp_recipe_color.py` 两个来源不同，均保留 main 版本。A/B 四文件不变，独立五槽、原厂全部风格、高对比度黑白、HDF、Fn、RAW保护与拍照路径保留。

集成 BIN 不能与独立 A/B BIN 混称相同，既有首张/预览修复验收不扩大为所有配置或其它机型验收。最终集成 BIN 的 A/B 与 film-timing 都另行执行回放验证。

| 集成产物 | SHA256 |
| --- | --- |
| GR III BIN | `1904a3aec7c0bc70c979b77291f6957af3673d12450dd288747b40aff72e88b2` |
| runtime | `f711a570142bab490a86cffeaad62140b39631cf1689957084120e5b9cc1de78` |

136处组合 hook（含原有首张提交 hook）、A/B仍12处；无新增 A/B hook。RTOS增长944720字节，预算不变。诊断 build `b9b87b3a`，`producer_sites=[0x5351ae44]`。124个源指纹逐一匹配；BIN中的 runtime 与输出逐字节一致，已无 `A/B:` 字符串。通用构建 receipt 的 `camera_tested:false` 保留，不把用户单个候选反馈改写成全部生成配置均验收。

## 验证

- 完整 Node：311项，301通过、0失败、10跳过，187.395秒。历史Python备份、GR II/GRLife样本缺失占8项；另外两项因独立目录缺少本地800T/组合fixture跳过，补齐既有fixture后单独运行两个文件3/3通过（180.058秒，含一个原已通过检查），覆盖独立800T、错误分支拒绝及8种扩展组合的debug/release逐字节校验。
- ARM A/B、宿主/菜单/ADJ、原厂文字树、首张、配方与预览：263/263通过，197.281秒。
- 最终集成 BIN 的 film-timing、五槽配方与共享HDF：19/19通过，14.330秒。
- 最终 BIN A/B 实际 Base phase过滤/物理DISP解码、双入口、同/异tone普通ADJ OK与返回：通过；正式tone `11→16→11`。MENU5/ADJP26/ADJL27启用/关闭委派序列一致，A/B转换不调用控件或同步logger，重复DISP不重开选择器。
- 部署保护与GR IV codec：24/24通过，17.188秒。首次并发运行的中断测试在5秒等待构建入口前超时，未进入被测中断阶段；单独重测1/1与停止并发后的完整24/24通过，部署脚本/断言未修改，初始失败记录保留。
- guide/changelog/部署HTTP控制：13/13通过；changelog针对完整基线SHA校验通过。独立只读审查未发现重要问题，核实本次没有覆盖成像producer。

验证文件保存在忽略目录 `builds/gr3-ab-release-20261022/evidence/`；包括源比较、回放、初始与最终测试输出。发布由 main/develop普通原子推送触发既有 Deploy Baota，最终以本次完整SHA的 `DEPLOY_OK ... service=active` 和公网首页、工作台、guide、changelog核验为准，不以推送成功代替部署成功。
