# GR III 裁切菜单合并候选

基线 b5d6b7f，分支 daily/gr3-zoom80-fix。原厂 MENU 裁切入口同时选择和编辑焦距：关闭、第一档、第二档三行；上下选择，左右1mm调整28–100mm，OK保存并启用后返回，MENU放弃当前草稿并返回。切行丢弃未确认草稿；浏览、调节不写存储、不调用原厂倍率setter。原有两档存档格式和ADJ快速切档保留，设置页重复编辑项移除。网页影像方案的可选初始写入沿用。

## 实现证据

原厂SHA固定的TopMenu descriptor 53b36dec第28行原路由02000074（渲染器531978d8，倍率标题路径53197904）改为已有私有路由0200f105。原厂loader执行确认其余所有旧行路由不变，Setup仅增加胶卷/水印/胶卷名三行；HDF组合为四行。独立Node回读要求同一入口补丁。IIIx关闭焦距功能时不改原厂裁切入口；IV仍为独立实现。

菜单使用原有owned controller/view，状态仍位于既有union容量内，不增加任意全局RAM或改变controller大小。只有OK才保存并应用；应用失败保留已经提交的数值以便重试，避免重复写存储。确认相同倍率时仅在前端和后端都已匹配时跳过setter，仍确认档位身份。

## 离线检查

- Python相关菜单、存储、原厂loader、ARM控制器/视图、机型隔离115项通过。
- 最终BIN解码后的ARM capture检查1项通过，最终RTOS原厂裁切入口值为0200f105。
- 独立审查未发现未解决P1/P2，审查者另行执行70项相关测试通过。
- Node首轮321项309通过、10跳过、2失败：隔离工作区缺GR IV三张校准样本，以及上一提交新增globalZoom分支对应的旧UI正则。已补齐本地样本并更新明确的分支合同，相关11项单独复验通过。最终完整重跑321项：311通过、10项因可选样本缺失跳过、0失败（builds/unified-zoom-full-node-final.log）。
- ZIP结构与SHA256SUMS校验全部通过。

## 候选身份

产物：builds/m10v-gr3-unified-zoom-20261023/m10v-gr3-unified-zoom-20261023.zip。

- GR III 2.10，build_id 58accd97，debug启用，初始两档50/80mm，启用画幅/水平仪/负片颗粒。
- BIN SHA-256：35438f4decc8df1b3af7c8f538d3c968a41125571ddbe5d742bb04d51bb17a71。
- ZIP SHA-256：191f95541c489e7909bebf6bd6733830cca4c75ce08aef1400ed67e4cff81824。
- 构建：node scripts/build_gr3_zoom_diagnostic.mjs builds/m10v-gr3-unified-zoom-20261023 docs/testing/gr3-unified-zoom-20261023.txt。

80mm死机仍未离线复现，不能将菜单合并标记为该故障修复。候选包含之前的210/211/212日志；按README实测菜单及50→80mm切换，取回匹配此build_id的M10VCP0/1.BIN继续定位。物理按键、完整取景、JPEG/DNG、重启及故障恢复尚未真机验收。此候选未合并main、未推送GitHub或部署宝塔。
