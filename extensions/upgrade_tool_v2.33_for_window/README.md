#命令行开发工具用户手册
发布版本：1.0
作者邮箱：liuyi@rock-chips.com
日期：2021-08-26
文档密级：公开资料
前言
概述
命令行开发工具为开发人员提供了固件烧录|镜像烧录|设备擦除|设备切换|存储切换等功能。
支持芯片
3308|3326|3399|3328|3228h|3229|3368|3228|3288|3128|3126|3188|3036|1808|px30|1109|1126|35
66|3568
读者对象
本文档主要适用于开发人员
修订记录
日期 版本 工具版本 作者 修改说明
2021-08-26 V1.0 V2.0 刘翊 初稿
2023-10-18 v1.1 v2.17 刘翊 增加spi nand擦除步骤
[TOC]
1. 常用功能
1.1 查看升级设备
upgrade_tool ld

可升级设备统称为Rockusb,有两种Loader和Maskrom
1.2 下载Boot
当可升级设备在Maskrom时，需要先下载Boot才能进行通讯,Boot下载过程不会写设备存储
upgrade_tool db rkxxloader.bin
问题处理:
问题1:请检查DDR或者主控,重试请先重启设备
问题2:请检查USB,重试请先重启设备
1.3 烧写Loader
此操作可以在Maskrom或者Loader下进行，烧写loader的过程会下载Boot,同时会生成IDBlock写
入设备存储
//烧录loader并重启设备
upgrade_tool ul rkxxloader.bin
//烧录loader不重启设备
upgrade_tool ul rkxxloader.bin -noreset
//当设备存在多个存储，需要指定loader烧录的目标存储，本例为spinor
upgrade_tool ul rkxxloader.bin SPINOR
问题处理：
问题1:请检查DDR或者主控,重试请先重启设备
问题2:请检查USB,重试请先重启设备
问题3:请检查Flash是否在支持列表或者硬件虚焊
问题4:通讯异常,概率出现时检查usb连接,必现时检查设备端
1.4 烧录分区镜像
注意:烧录分区镜像前,需要先烧录分区表

//烧录分区表
upgrade_tool di -p parameter.txt
//烧录单个分区镜像
upgrade_tool di -k kernel.img
//烧录多个分区镜像
upgrade_tool di -u uboot.img -b boot.img
//烧录未定义缩写的分区镜像,需要用分区名来指定，这里以vendor分区为例
upgrade_tool di -vendor vendor.img
//当使用ab分区时，也需要按未定义的情况处理，这里以boot_a和boot_b为例
upgrade_tool di -boot_a boot.img -boot_b boot.img
//已定义缩写的分区有
-b:boot
-k:kernel
-r:recovery
-s:system
-u:uboot
-m:misc
-t:trust
问题处理:
问题1:请检查镜像文件是否存在或被占用
问题2:分区定义过小,镜像过大的情况
问题3:请检查USB,重试请先重启设备
1.5 设备切换
//loader切换到maskrom
upgrade_tool rd 3
1.6 升级固件
此操作可以在Maskrom或者Loader下进行，烧写loader的过程会下载Boot,无需提前下载Boot
//烧录升级固件并重启设备
upgrade_tool uf update.img
//烧录升级固件不重启设备
upgrade_tool uf update.img -noreset
问题处理:
问题1:请检查固件是否存在或者被占用

问题2:固件标识错误,请检查固件打包过程
问题3:固件摘要检查失败,请确认固件是否被修改
问题4:固件读取失败,请更新固件打包工具重新生成固件
问题5:固件中存在分区定义过小,镜像过大的情况
问题6:固件中芯片标志不正确，请使用工具读取芯片信息后,重新生成固件
问题7:通讯异常,概率出现时检查usb连接,必现时检查设备端
1.7 按地址读写文件
//按地址写文件到LBA 0x12000
upgrade_tool wl 0x12000 oem.img
//按地址读数据保存到文件,例子:从0x12000开始读取0x2000扇区数据到out.img
upgrade_tool rl 0x12000 0x2000 out.img
1.8 设备擦除
//擦除存储的所有数据,请进入maskrom执行,不需要提前下载Boot(支持emmc和nand)
upgrade_tool ef rkxxloader.bin
//按地址进行扇区擦除,支持emmc|spinand|spinor,例子:从第0扇区开始擦除0x2000个扇区
upgrade_tool el 0 0x2000
//擦除spinand所有数据
1.upgrade_tool db rkxxloader.bin(进入maskrom模式执行)
2.upgrade_tool el 0 -1
1.9 读取设备信息
//读取存储信息
upgrade_tool rfi
//读取芯片id
upgrade_tool rci
//读取分区表
upgrade_tool pl
1.10 多存储操作
当设备上存在多个存储器件时可以进行存储器件间的选择，操作需要在maskrom下进行，进行前
要保证下载boot成功

upgrade_tool ssd
执行命令后,会列出当前可以选择的存储，带*的为当前存储，输入存储前的No进行选择
1.11 多设备选择
当有多个设备同时连接时，先用LD命令列出所有设备，记录下要操作设备的LocationID,操作时
用-s参数指定
//对LocationID为100的设备进行loader升级
upgrade_tool -s 100 ul rkxxloader.bin

