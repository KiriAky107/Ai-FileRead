# 环境配置
部署好项目后，一般在终端都显示目前操作路径为 xx\FilesReadSystem
在终端输入：
```bash
cd backend
```
以进入后端项目目录
此时终端显示目前操作路径为 xx\FilesReadSystem\backend
接着在终端输入：
```bash
python312 -m venv venv
```
以指定python创建python虚拟环境，可确保软件包不会与系统python版本冲突
创建虚拟环境成功后，在终端输入：
```bash
.\venv\Scripts\Activate.ps1 #如果你的终端是powershell，请使用此命令
.\venv\Scripts\Activate.bat #如果你的终端是cmd，请使用此命令
```
激活虚拟环境成功后，在终端输入：
```bash
pip install -r requirements.txt
```
以安装项目需要的依赖包
