# 胶卷多选与中文菜单 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 将五槽换卷替换为最多10卷启用列表，并统一清晰方形图标和中文菜单。
**Architecture:** 以已发布main为基线独立开发；扩展持久化及捕获合同，再接入动态影像控制和两排网格。相机资源和网页资源共用生成源。
**Tech Stack:** C/ARM、Python资源构建、Node、原生网页。
**Spec:** docs/superpowers/specs/2026-10-23-film-multiselect-design.md

## Global Constraints
- 最多10卷；每页5列×2排；按勾选顺序追加至Custom2下方。
- 原厂效果及Custom1/2保留；全部操作和错误文案尽量中文。
- 当前视觉确认前不发布；保留原工作区，不夹带其他功能改动。

## Review Focus
- 旧五槽重复卷及损坏存档：可恢复迁移，参数不静默混淆。
- 移除活动卷及排队照片：原厂标准回退，已拍摄快照不变。
- 满10卷、0卷及SD目录变化：合法列表，无越界或陈旧ID写入。
- 保存失败与重启：保留最后成功提交，菜单和捕获引用一致。
- IIIx/IV独立ABI：拒绝不支持的组合，不套用III地址。

### Task 1: 视觉确认与资源统一
**Files:** scripts/generate_m10v_icons.py, scripts/generate_m10v_film_cards.py, native/gr3/m10v_film_card.c, web/gr3/film-icons/*
- [x] 生成中文多选菜单预览。
- [x] 用户确认视觉后，将方形平滑字体资源统一为可重现生成源，覆盖87款内建卷和自定义卷。

### Task 2: 十卷持久化与捕获合同
**Files:** native/gr3/m10v_library.h/.c, m10v_library_camera.c, m10v_library_capture.c, m10v_sd_camera.c, node/gr3-native-library.mjs, web/gr3/native-library-state.mjs
- [x] 定义新存档版本、0..10数量和稳定卷身份；迁移旧五槽，重复卷取首项。
- [x] 增加原子启用/停用接口，满额拒绝、失败回滚、活动卷回退。
- [x] 更新渲染/排队快照及SD消费者的边界和身份校验，保留旧文件读取。

### Task 3: 影像控制与中文网格
**Files:** native/gr3/m10v_tone.h, m10v_tone_menu.c, m10v_settings*.c/.h, scripts/build_gr3_film_slot_extension.py, scripts/build_gr3_settings_hooks.py
- [x] 动态枚举0..10已选卷，保留原厂和Custom1/2、视频与RAW开发边界。
- [x] 5×2网格、跨行翻页、勾选状态、中文计数和上限提示，替换槽位入口。
- [x] 同步ADJ、详细参数及A/B引用，不让移除造成悬空引用。

### Task 4: 网页与各机型集成
**Files:** web/gr3/native-library.*, sd-library.*, node/gr3-native-library.mjs, scripts/build_gr3_m10v_library.py, native/gr4/*
- [x] 网页多选与10卷参数配置、导出合同及初始状态一致。
- [x] 逐机型核对资源/结构与边界，未支持路径明确拒绝。
- [x] 按用户跳过测试要求记录实际跳过项；保留必要构建校验，更新changelog；视觉确认后按当前授权发布并核验实际SHA及上线结果。

执行说明：用户已确认视觉和直接发布，并明确跳过测试套件；完成语法、正式构建、固件回读与独立代码复查。发布结果以GitHub Actions及线上核验记录为准。GR IV保留私有五位置菜单，未扩展为十卷。
