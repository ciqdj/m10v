# M10V 名字来源的固件证据

核对样本：`bin/fwdc239b-gr3-official.bin`，GR III Street Edition 2.10。

通过项目的官方容器解码器读取 INITFS 分区，头部为 ROMFS v1 (`-rom1fs-`)。其中的 `initramfs` 文件为 gzip 压缩的 newc CPIO 归档。只读解析归档中的 `etc/hostname`，得到文件内容 `m10v\n`。

这证明官方样本的 Linux 根文件系统主机名配置为 m10v。说明页据此讲述项目名称来源，不把它描述为互联网服务器的名称，也不推断厂商为什么选择这四个字符。说明页中围绕拍摄和定制的文字属于项目叙事。
