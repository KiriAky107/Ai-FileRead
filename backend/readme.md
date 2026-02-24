## 技术栈

| 层次     | 组件                                        | 说明                              |
| :------- | :------------------------------------------ | :-------------------------------- |
| 前端     | Vue 3 / React + Element Plus                | 文件上传、表格配置、聊天界面      |
| 后端     | FastAPI                                     | 提供 RESTful API，异步任务调度    |
| 异步任务 | Celery + Redis                              | 处理耗时的解析与 AI 提取          |
| 数据库   | MongoDB（元数据、提取结果）                 | 存储文档块、最终结构化数据        |
| 向量检索 | faiss-cpu + 本地索引文件                    | 高效相似性搜索，配合 MongoDB 使用 |
| AI 集成  | LangChain + 国内大模型 API                  | RAG 流水线、提示词管理            |
| 文档解析 | python-docx, pandas, markdown, 原生文件操作 | 多格式支持                        |
| 部署     | Docker + Nginx + Gunicorn                   | 打包演示，本地或云服务器运行      |

## 环境配置

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


