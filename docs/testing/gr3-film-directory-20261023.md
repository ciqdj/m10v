# 2026-10-23 胶卷目录重组与光谱重做验证

> **旧候选已撤回**：用户实机反馈进入胶卷库黑屏，可关机。请改用[黑屏修复r1](gr3-film-directory-black-screen-r1-20261023.md)，不要继续使用本页原6fb3855d测试包。

状态：**WAITING_FOR_USER_VALIDATION**。本次交付 GR III 官方 2.10 的本地测试包；尚未真机验收，未合并 main、推送或部署。实现基于 `41f6f777ee4abe5c25ef74a9bfd693eb335dbb66`，代码版本 `fdc09f9d640840b268faae4e25dfd5910467dfa0`，分支 `daily/film-catalog-order-20261023`。原脏工作区保持原样，改动位于隔离工作树。

测试包：[M10V GR III fdc09f9 ZIP](../../builds/M10V-GR3-film-directory-20261023-fdc09f9.zip)，附 `.sha256` 与包内 `SHA256SUMS`。

## 目录合同

后台 API、选择器、SD 新导出与机内分组共用 `web/gr3/film-directory.json`。仅显示用户指定的五组、30 项，Cyanotype 去重；分组顺序与组内顺序逐字比较。完整清单见 [确认规格](../superpowers/specs/2026-10-23-film-catalog-order-design.md)。Pixel Worlds 复用原像素风 ID290，Lomography 对应原 Color Negative400；Fuji Industrial100 / Lucky C200 保持原富士业务用100 / 乐凯C200身份。后两款保留现有效果的近似局限，未声称实拍标定。

未列项目从新可选目录与新固件配置中移除。旧 ID、旧卡记录及自定义 LUT 解码保留，不将旧 ID 赋给新胶卷。5213独立使用298，不占自定义79..288或原风格291..297。

原有已启用的退役胶卷可能占满十槽。机内五个分组后有独立的“清理已停用胶卷”操作，按 OK 才逐项调用既有删除/回读事务；浏览、换组和取消零写卡。清理会移除这些卷的启用状态，保留数据文件和照片；每次删除独立提交，失败后保留已完成的删除并显示错误，重新操作可继续。后台恢复旧草稿时剔除退役项，保留其余卷参数；后端拒绝用退役项构建新包。

SD菜单按稳定ID从同一个已验证头页查找，旧卡和子集顺序不串卷；已有物理页索引 API 保持原意。5213快照用独立 `M10VS09.bin`，不覆盖像素风和既有风格快照。A/B原生列表补齐5213和保留风格的完整名称/图标。

## 2460 / 5213来源与误差

2460为 Kodak AeroColor IV Negative Film2460，参考 [Kodak AS-2652](https://www.kodak.com/content/products-brochures/Advanced-Materials/KODAK-AEROCOLOR-III-Negative-Film-2460-datasheet.pdf) 与 [Jan Lohse同型号光谱模型](https://janlohse.github.io/spectral_film_lut/reference/negative_film/kodak_aerocolor/)。按用户要求显示在ECN2；官方实际工艺AN-6/C-41单独记录。移除旧任意22%曲线混合，使用完整负片→Portra Endura印相纸→sRGB链路，无橙色掩膜，不采用上游复制5207的颗粒参数。

5213使用其独立KODAK_5213数据，参考 [Kodak历史技术数据](https://www.kodak.com/content/products-brochures/Film/VISION3-200T-Color-Negative-Film-7213-TECHNICAL-DATA.pdf)，固定2015含remjet版本，不冒充5207/5219，不宣称标定2026新背涂版本。完整参数、源码哈希、LUT哈希和拟合系数见 `native/gr3/spectral-reference.json`。

8192个独立固定随机样本；ΔE00为与明确模型的算法误差，**不是与实体胶片实拍的误差**：

|目标|LUT median / p95 / max|取景近似 median / p95 / max|
|---|---|---|
|2460|0.2544 / 0.9865 / 4.8204|2.179 / 6.898 / 21.032|
|5213|0.2089 / 0.8466 / 4.1341|1.381 / 3.661 / 11.160|

取景近似不能替代JPEG LUT。两卷强制走静态CPU颜色LUT，原生完成标志不得跳过；因此真实相机的时延、颜色和稳定性仍需验收。输入为ISP后的编码sRGB，不是反演恢复的场景光谱。无物理100%还原声明。

## 验证结果

- 目录/API/SD/预览/旧草稿相关Node测试：**21/21通过**。
- Python生产C/ASan菜单、光谱黄金样本、ARM SD（4例）、原生ARM A/B资源映射：**7/7通过**。覆盖五组6/14/1/6/3项、C41两页、子集空洞、取消零写、十槽上限、旧满额清理/失败、77/298静态颜色不被完成标志跳过、stride不越界、旧55项真实卡、损坏与关闭失败不写存档。
- `verify_gr3_spectral_reference`通过；重新生成目录C与SD哈希合同无差异。独立审查还完整重算两套3375点网格，与提交LUT哈希完全一致。
- 完整 `npm test`：**345项，298通过、40失败、7跳过**。隔离的原始主线基线：338项，291通过、40失败、7跳过。失败名称集合完全相同，**新增失败0**。全量套件仍未全绿，不能据此宣称完整产品验收通过。
- 后台浏览器实查五组和全部30名称顺序；[截图](../previews/film-directory-20261023.png)。未以浏览器截图代替相机LCD验证。
- 最终固件SHA-256：`6fb3855dccc9bfbb6ea991446884eec45a834edf1e83b49960844c2ca0db2164`，32,126,240字节。

最终候选沿网页同一CLI导出链构建：147挂钩回读，775项资源图标目录，内部兼容88条配方/新目录30条，十槽schema5/184字节。RTOS增长1,110,988字节，低于原上限1,130,496，未放宽限制。

## 保留和取舍

|路径|本次处理与验证边界|
|---|---|
|原厂预设、十槽、Custom1/2|保持既有追加槽与存档ABI，未自动清空用户配置；物理切换/恢复待设备验收|
|JPEG、RAW、取景|仅77/298的颜色数据和必要分派改变；RAW所有权不扩展，取景仍近似；拍摄、回放、连拍待实机|
|颗粒、光晕、EI、水印、HDF与扩展|保留现有入口/效果，候选147挂钩与构建回读；这些功能不由本轮离线测试扩大设备证明范围|
|自定义与退役卷|保留解码/身份；新30项选择器不再显示；显式清理只改启用状态|
|5213对象布局|新LUT与最后一组只读风格对象共用C编译单元，以满足既有单对象64KiB约束；效果身份和数据独立|
|原工作区/发布|使用隔离工作树；不修改原脏分支，不推送或部署测试候选|

一次独立整分支审查发现两项重要问题：旧卡满额无法删除、5213在A/B误标。两项均已修复并用生产C/ARM测试验证；没有重复发起审查。

## 基线同名40项失败

以下为两次隔离执行得到的相同失败名称，包含旧v4/五槽断言、既有SD历史夹具、集成与资源审计等。它们仍需另行修复，本次没有删测或放宽生产校验掩盖：

- 800T routes require local token and matching preflight before audited BIN download
- 800T weak without timestamp produces an independently audited container
- GR III preflight preserves factory choices and binds the new slot layout to approval
- GR IIIx ports audited legacy recipe, timestamp, aspect and level composition with stock edits
- GR IV actual native capabilities and custom prepare are model-specific
- GR IV import uses the shared workflow and isolated native endpoints
- Phoenix EI120 persists independently per slot and resets on a different stock
- abort while checking fitter availability cannot be missed
- aborted firmware request terminates its child and cleans the owned temporary folder
- accepted-plan audit rejects a wrong branch even when writer expectation agrees
- both colour views edit a single native configuration and do not restore the legacy film builder
- complete identity Look is rendered locally and fitted to GR III matrices
- deleting texture processing retains all55 previous-revision film records
- diffusion cannot export before independent GR III descriptor isolation evidence
- diffusion hook, frozen code and per-tone levels are read back independently of receipt
- digital HDF is independent of films and retired soft values never become HDF
- film name stamp migrates off and packs independently from date
- final joined firmware contains all selected components and rejects repaired-checksum tampering
- four colors persist per slot, texture reset preserves color and switching film clears it
- four halo controls and grain/soft are packed in each version4 slot
- fresh defaults and every film selection leave extra effects off
- fresh journals preserve independent timestamp corner and colour bytes
- independent settings audit binds owned controllers, original fallback and root captions
- last delivered 47-film and named custom packs remain readable after opt-in defaults
- legacy effects serialize as neutral and resetting preserves film and special controls
- legacy retired effects migrate to neutral without losing other slot settings
- local sample selection does not override the loaded target until import completes
- native RAW NR export independently reads back off and threshold together with old extensions
- old effects upgrade and film-specific bounds accept bounded integer simulated EI
- old web configuration migrates into v4 and validates effect ranges
- original M10V web workflow binds all five slots and timestamp into audited firmware
- prior renderer custom LUTs remain accepted while repaired-CRC tampering is rejected
- product home exposes GR IV native workbench and GR II inspection with truthful limits
- real GR III build stores correct grain strengths and preserves Positive shared branch
- schema4 packs EI in each effects reserved byte and common reset preserves EI and disables extra effects
- single studio orders source, settings and save with the library embedded directly
- switching away from a manually enabled effect resets extras, selecting same film preserves them
- the same import handler accepts both models and updates target labels from official identity
- v1 built-in pack from the preceding release remains readable
- web debug export uses the running Node when the service PATH contains no node
