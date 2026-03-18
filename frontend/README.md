

## 介绍

项目介绍

## 目录结构

```
├── README.md # 说明文档
├── components.json # 组件库配置
├── index.html # 入口文件
├── package.json # 包管理
├── postcss.config.js # postcss 配置
├── public # 静态资源目录
│   ├── favicon.png # 图标
│   └── images # 图片资源
├── src # 源码目录
│   ├── App.tsx # 入口文件
│   ├── components # 组件目录
│   ├── contexts # 上下文目录
│   ├── db # 数据库配置目录
│   ├── hooks # 通用钩子函数目录
│   ├── index.css # 全局样式
│   ├── layout # 布局目录
│   ├── lib # 工具库目录
│   ├── main.tsx # 入口文件
│   ├── routes.tsx # 路由配置
│   ├── pages # 页面目录
│   ├── services  # 数据库交互目录
│   ├── types   # 类型定义目录
├── tsconfig.app.json  # ts 前端配置文件
├── tsconfig.json # ts 配置文件
├── tsconfig.node.json # ts node端配置文件
└── vite.config.ts # vite 配置文件
```

## 技术栈

Vite、TypeScript、React、Supabase

## 本地开发

首先进行包安装：
```bash
cd frontend #进入前端目录
npm install #确定目录中有node_modules文件夹后输入命令安装依赖包
```

## 启动项目
启动项目：
```bash
npm run dev #启动项目，需要确保后端已启动，否则前端功能无法使用
```
启动后在终端ctrl+左键点击项目地址打开浏览器，一般是http://localhost:5173


记得在你根目录下的.gitignore文件中添加：

```bash
/frontend/node_modules/
/frontend/dist/
/frontend/build/
/frontend/.vscode/
/frontend/.idea/
/frontend/*.log
```