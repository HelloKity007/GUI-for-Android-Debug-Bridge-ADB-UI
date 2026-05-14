# eywa cmd和midleware调试命令

## 调用关系：

middleware命令 -> 调用系统接口或调用eywa接口

eywa命令->调用driver或其他hardware接口

## eywa命令：

### 1.1 GPIO 相关命令

如GPIO number为394则命令是

拉高电平：xbhfunc_new XbhApi_setGpioOutputValue 394 1

拉低电平：xbhfunc_new XbhApi_setGpioOutputValue 394 0

读输出电平：xbhfunc_new XbhApi_getGpioOutputValue 394

读输入电平：xbhfunc_new XbhApi_getGpioInputValue 394



## middleware命令：

### 1.1 GPIO 相关命令

如GPIO number为394则命令是

拉高电平：xbhfunc_new setGpioOutputValue 394 true

拉低电平：xbhfunc_new setGpioOutputValue 394 false

读输出电平：xbhfunc_new getGpioOutputValue 394

读输入电平：xbhfunc_new getGpioInputValue 394
