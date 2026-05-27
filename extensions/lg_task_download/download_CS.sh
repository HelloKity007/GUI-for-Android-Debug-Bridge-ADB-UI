#!/bin/bash

export LC_ALL=C.UTF-8
export LANG=C.UTF-8

taskName=$(echo $1 | cut -d'=' -f2)
localPath=${2:-$(pwd)} # 如果没有传入localPath参数，则默认存放在当前目录

echo "Task name: $taskName"
echo "Local path: $localPath"

# 定义需要进行编码的字符的关联数组变量
declare -A to_encode=(
	["低存储检测对策"]="%E4%BD%8E%E5%AD%98%E5%82%A8%E6%A3%80%E6%B5%8B%E5%AF%B9%E7%AD%96"
	["资料卡"]="%E8%B5%84%E6%96%99%E5%8D%A1"
	["请解压"]="%E8%AF%B7%E8%A7%A3%E5%8E%8B"
	["芯片"]="%E8%8A%AF%E7%89%87"
	["刷机"]="%E5%88%B7%E6%9C%BA"
	["差分"]="%E5%B7%AE%E5%88%86"
	["屏参"]="%E5%B1%8F%E5%8F%82"
	["电脑"]="%E7%94%B5%E8%84%91"
	["文件"]="%E6%96%87%E4%BB%B6"
	["工厂"]="%E5%B7%A5%E5%8E%82"
	["方法"]="%E6%96%B9%E6%B3%95"
	["闪烁"]="%E9%97%AA%E7%83%81"
	["灵动"]="%E7%81%B5%E5%8A%A8"
	["升级"]="%E5%8D%87%E7%BA%A7"
	["系统"]="%E7%B3%BB%E7%BB%9F"
	["固件"]="%E5%9B%BA%E4%BB%B6"
	["烧录"]="%E7%83%A7%E5%BD%95"
	["软件"]="%E8%BD%AF%E4%BB%B6"
	["客户"]="%E5%AE%A2%E6%88%B7"
	["生产"]="%E7%94%9F%E4%BA%A7"
	["维修"]="%E7%BB%B4%E4%BF%AE"
	["串口"]="%E4%B8%B2%E5%8F%A3"
	["【"]="%E3%80%90"
	["】"]="%E3%80%91"
	["（"]="%EF%BC%88"
	["）"]="%EF%BC%89"
	["盘"]="%E7%9B%98"
	["及"]="%E5%8F%8A"
	["包"]="%E5%8C%85"
)

# 请求 web 服务端接口，获取文本内容
text=$(curl -s "http://192.168.21.2:8080/auditServer/commServer/resource/downloadTaskTxt?taskName=$taskName")

# 将文本内容按分号分割成数组
IFS=';' read -ra pairs <<< "$text"

# 遍历数组，下载文件到本地目录
for pair in "${pairs[@]}"; do
    IFS=',' read -r key value <<< "$pair"
    filename=$(basename $value)
    escaped_value=$value
    for char in "${!to_encode[@]}"; do
        escaped_value=${escaped_value//$char/${to_encode[$char]}}
    done
    echo "Replacing URL: $value => $escaped_value"
    filepath="$localPath/$key/$filename"
    echo "Downloading $escaped_value to $filepath..."
    mkdir -p "$localPath/$key"
    if [ "$filepath" == "$localPath/$filename" ]; then
        curl -# -o "$localPath/$key/$filename" "$escaped_value"
        rm "$localPath/$filename"
    else
        curl -# -o "$filepath" "$escaped_value"
    fi
    echo "Download succeeded"
done