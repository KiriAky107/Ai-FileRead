> [!TIP]
>
> 注意，本文档仅为前端开发过程中团队交流使用，非正式的readme文档。


> 以下为官方自带说明，请忽略（正文开始在下面）

# 前端项目说明

这是一个使用 Vue 3 和 Vite 的模板项目，帮助您开始开发。

## 推荐的 IDE 设置

[VS Code](https://code.visualstudio.com/) + [Vue (官方)](https://marketplace.visualstudio.com/items?itemName=Vue.volar)（并禁用 Vetur）。

## 推荐的浏览器设置

- 基于 Chromium 的浏览器（Chrome、Edge、Brave 等）：
  - [Vue.js 开发者工具](https://chromewebstore.google.com/detail/vuejs-devtools/nhdogjmejiglipccpnnnanhbledajbpd)
  - [在 Chrome DevTools 中开启自定义对象格式化程序](http://bit.ly/object-formatters)
- Firefox：
  - [Vue.js 开发者工具](https://addons.mozilla.org/en-US/firefox/addon/vue-js-devtools/)
  - [在 Firefox DevTools 中开启自定义对象格式化程序](https://fxdx.dev/firefox-devtools-custom-object-formatters/)

## TypeScript 对 `.vue` 导入的类型支持

TypeScript 默认无法处理 `.vue` 导入的类型信息，因此我们用 `vue-tsc` 替换了 `tsc` 命令进行类型检查。在编辑器中，我们需要 [Volar](https://marketplace.visualstudio.com/items?itemName=Vue.volar) 让 TypeScript 语言服务识别 `.vue` 类型。

## 自定义配置

参见 [Vite 配置参考](https://vite.dev/config/)。

## 项目设置

```sh
npm install
```

### 编译和热重载用于开发

```sh
npm run dev
```

### 类型检查、编译和生产环境压缩

```sh
npm run build
```

### 使用 [ESLint](https://eslint.org/) 进行代码检查

```sh
npm run lint
```

## vscode设置
首先在插件库中安装`Vue`插件
![alt text](image\image-3.png)
选择官方的即可

## 构建
在安装完`Node.js`后
直接在项目根目录下（即xxx\FileReadSystem\）下运行
```sh
npm create vue@latest
```
项目名直接用frontend
随后的选择如下:
```
✔ Project name: … frontend
✔ Add TypeScript? … **Yes**  (推荐，更好的类型支持)
✔ Add JSX? … No / Yes  (根据需要，一般不需要)
✔ Add Vue Router for Single Page Application development? … **Yes** (需要路由)
✔ Add Pinia for state management? … **Yes** (推荐，状态管理)
✔ Add Vitest for Unit Testing? … No (测试，可以暂时不选)
✔ Add an End-to-End Testing Solution? … No (端到端测试，暂时不选)
✔ Add ESLint for code quality? … **Yes** (代码规范)
✔ Add Prettier for code formatting? … **Yes** (代码格式化)
```

实验特性不选就行

跳过所有示例代码，创建一个空白的Vue项目 Yes

完成后输入
```sh
cd frontend
#随后输入
npm install #确保frontend目录下有package.json文件
```
安装包完成后输入
```sh
npm run dev
```
以进入调试
若终端出现：
![alt text](image\image-4.png)
说明构建成功，ctrl+鼠标左键点击第一个网址即可查看当前页面
在终端输入q即可退出调试

## 关于`.gitignore`

根目录下`.gitignore`文件修改如下：
```sh
/.git/
/.gitignore
/.idea/
/.vscode/
/backend/venv/
/backend/command/
/backend/.env
/backend/.env.local
/backend/.env.*.local
/backend/app/__pycache__/

# 前端忽略
/frontend/* 
!/frontend/README.md
!/frontend/image/
# 在你自己构建好后，请删除上面这三行
/frontend/node_modules/
/frontend/dist/
/frontend/build/
/frontend/.env
/frontend/.vscode/
/frontend/.idea/
/frontend/*.log
```
