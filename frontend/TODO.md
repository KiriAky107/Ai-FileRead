# Task: 基于大语言模型的文档理解与多源数据融合系统

## Plan
- [x] 数据库初始化与权限配置 (Supabase)
  - [x] 创建 `profiles` 表及触发器 (登录同步)
  - [x] 创建 `documents` 表 (存储上传的文档信息)
  - [x] 创建 `extracted_entities` 表 (存储从文档提取的结构化数据)
  - [x] 创建 `templates` 表 (存储表格模板)
  - [x] 创建 `fill_tasks` 表 (存储填写任务)
  - [x] 配置 RLS 策略 (Row Level Security)
  - [x] 创建 Storage 存储桶 `document_storage` (存储文档和模板)
- [x] 基础架构与登录模块
  - [x] 配置路由 `@/routes.tsx`
  - [x] 创建登录/注册页面
  - [x] 实现 `AuthContext` 与 `RouteGuard` (登录状态管理)
  - [x] 创建系统主布局 `MainLayout` (含侧边栏导航)
- [x] 文档上传与智能提取功能
  - [x] 实现文档上传组件 (支持 docx, md, xlsx, txt)
  - [x] 部署 Edge Function `process-document` (调用 MiniMax 处理文档提取)
  - [x] 实现文档列表与详情页 (显示提取的结构化数据)
- [x] 表格模板与自动填写模块
  - [x] 实现模板上传与管理
  - [x] 部署 Edge Function `fill-template` (基于提取数据填充表格)
  - [x] 实现任务监控与结果下载
- [x] 智能对话交互模块
  - [x] 实现智能助手聊天界面 (侧边栏或独立页面)
  - [x] 部署 Edge Function `chat-assistant` (解析自然语言指令执行操作)
- [x] 系统优化与美化
  - [x] 全面应用科技蓝办公风格 (index.css, tailwind.config.js)
  - [x] 响应式适配 (移动端兼容)
  - [x] 完善错误处理与加载状态 (Skeleton, Toast)

## Notes
- 所有 Edge Functions 已部署并集成 MiniMax API
- 文档解析使用 mammoth (docx), xlsx (excel), 原生 TextDecoder (txt/md)
- 系统采用科技蓝主题，支持暗色模式
- 所有代码已通过 lint 检查
