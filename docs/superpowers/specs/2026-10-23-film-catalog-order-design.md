# 胶卷目录、名称与排序

用户在本轮确认：仅保留以下五组共 30 项；Cyanotype 只出现一次；Pixel Worlds 复用原「方块世界」像素风（稳定 ID 290）；Lomography 沿用 Color Negative 400；Fuji Industrial 100、Lucky C200 对应原「富士业务用 100」「乐凯 C200」。括号补充不进入名称。

1. ECN2：800T、5207、5219、5203、5213、2460
2. C41：Portra 160、Portra 400、Fuji Industrial 100、Fuji C200、Fuji Superia 200、Fuji Pro 400H、Kodak Gold 200、Kodak UltraMax 400、ProImage 100、Ektar 100、Lucky C200、Harman Phoenix II、Harman Red、Lomography
3. D76：T-Max 100
4. 创意：Kodak Charmera、CCD、Polaroid、Cyanotype、Pixel Worlds、Aerochrome
5. 影像：Leica Monochrome、German Cool、GR2

后台 API、选择器、图标说明、SD 记录、机内选择菜单及动态名称必须逐字一致。顺序来自同一目录，禁止按 ID、精选标签或字母重新排序。未列项目从可选目录移除；已存记录及自定义 LUT 身份仍保留解码，不能把旧 ID 复用为其他胶卷。十槽、其他机型 ABI、原厂效果、拍摄/回放/水印路径不因目录整理而回退。

## 实现方式

采用单一 JSON 目录生成 C 目录表，Node 与生成脚本读取同一来源。分别修改多处名称表和排序会继续产生漂移，因此不采用。目录记录稳定 ID 和显示顺序，两者独立。5213 为独立新胶卷，使用 298，不能占用 79..288 自定义 ID 或冒充 5207/5219。

机内按组分页，组内保持顺序，组标题使用 ECN2、C41、D76、创意、影像。浏览、换组和返回不写入配置，OK 保持现有勾选安装/移除与最多十项的语义。

## 2460 与 5213

2460 身份为 Kodak AeroColor IV Negative Film 2460，按用户指定归 ECN2；实际官方工艺 AN-6 / C-41 单独记录。用户接受按官方资料与同型号社区模型重做并量化验证，不承诺物理胶片 100% 还原。

参考 Kodak AS-2652（2009）：https://www.kodak.com/content/products-brochures/Advanced-Materials/KODAK-AEROCOLOR-III-Negative-Film-2460-datasheet.pdf （文件名 III，正文明确 IV 2460），及 Jan Lohse Spectral Film LUT 的 `KODAK_AEROCOLOR`。重做完整光谱负片/印放链路，去除旧模型的 22% 曲线混合和假设 RGB 高斯串色；固定输入、印相纸、白平衡、曝光和源码哈希。保留无橙色掩膜参数；上游复制自 5207 的颗粒数据不得宣称为 2460 实测。

5213 使用 `KODAK_5213` 自身数据，不用 EXR 5293 替代。官方资料：https://www.kodak.com/content/products-brochures/Film/VISION3-200T-Color-Negative-Film-7213-TECHNICAL-DATA.pdf 。固定历史数据版本，不能宣称覆盖 2026 新背涂版本。

报告浏览器/CPU LUT 采样误差、原生拟合误差与真正胶片误差的区别；设备未验收前保持 camera_tested=false，交付测试包，不推送或部署。

## 验收

独立字面量清单比对 30 项及五组；API、SD 包解析和 C 菜单遍历结果相同；名称、旧 ID 和自定义 ID 不串卷；组内分页、取消零写入、满十槽及旧卡错误回退覆盖。2460/5213 做固定随机样本与灰阶误差报告、最终 ARM/BIN 回读、构建大小与机型门禁检查。真机仍需按测试包身份核验名称、分组、顺序、选卷、首张/连续 JPEG 和回放。
