# GR3 800T 独立机内菜单

用户要求独立新增五项并保留原厂色彩控制。仅 Bleach/800T、拍摄详细设置显示新项，RAW开发不增加。原始18项ID和字符串保留；新ID18..22及字符串312..316。三组自定义设置分开保存。

1. ARM backend：主设置record的heap四处分配B28扩至B48，新增32B尾部；原厂B26文件格式不改；专用C:\M10V8CFG.BIN保存32B。检查指针、范围、版本、checksum和短读，默认3/3/5/2/0。原始SI字段完全不再充当控制源。
2. UI：复制列表为800T追加五项；扩展标题和字符串查询；复制原生slider初始化并沿用原生closure销毁和generic callback，增补新ID current/set/render分支。其他原厂ID按原路由执行。
3. 恢复五条原厂pipeline指令；capture/trace改从独立控制backend取值，保护控制record与pixel/scratch不别名。
4. 严格source preimage、代码无未解析重定位、append不重叠、ARM行为测试、全部section独立重建审计。构建诊断版并提供名称、范围、恢复/存储限制说明。

软件验证不等于机内实测；菜单字体、相机SD写入和开关机保留仍须新固件实机确认。
