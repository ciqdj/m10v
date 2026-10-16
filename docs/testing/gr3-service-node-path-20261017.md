# 宝塔网页导出 Node 路径修复

用户在已部署71dd3f7的网页构建GR III调试组合包时，Python调用SD契约生成器失败：FileNotFoundError node。systemd使用绝对路径启动Node，但服务PATH不含该Node目录；此前部署终端CLI烟测通过未覆盖实际服务环境。

修复：网页构建通过继承环境并设置M10V_NODE=process.execPath传入Python。Python优先采用此绝对路径，独立命令行则仍通过PATH查找Node；缺失时给出明确错误。没有调整systemd安全设置或全局PATH。

回归node/gr3-native-node-path.test.mjs以绝对路径启动Node，在只提供clang、不含node的PATH下通过真实HTTP执行导入、预检、调试组合导出，并验证36款SD能力、组合审计、画幅资源970及实际固件摘要。修复前准确复现用户同一行FileNotFoundError；修复后测试通过（约44秒）。胶卷包/独立菜单8项通过，发布保护11项通过；独立审查无P1/P2。

本次发布2026.10.17.2。线上实际网页构建结果以发布后的浏览器验收为准。
