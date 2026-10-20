# Vaelin UI 演示壳 · Desktop（DEMO · 非生产）

> **公开仓桌面演示窗** · 薄 Electron 壳 + 自洽拷贝的 fixture 静态资源 · 纯假数据 · **零接 Hermes**  
> **demo ≠ production** · **install ≠ enable** · 不是可分发安装包／不是已上架产品

## 演示 ≠ 生产

- 这是 **DEMO／非生产** 独立桌面窗，**不是** 生产 Vaelin，**不是** 已接 Hermes 的安装包
- 假数据 fixture；不接 vault／Hermes／SEALED／plugins
- 三模式（氧气／凯撒／玥）仍为壳内 **静态灰态**（无真接线）
- 未做代码签名、商店上架、自动更新、Program Files 安装、installer／Release 资产
- **禁公网隧道** · 静态服只绑 `127.0.0.1`

## 与 `demos/ui` 的关系

| | `demos/ui`（浏览器） | 本目录 `demos/desktop` |
|---|---|---|
| 打开 | `start_demo.bat` → 浏览器 `http://127.0.0.1:8765/` | `start_desktop.bat` → **独立 Electron 窗** |
| 端口 | 8765 | **8766**（占用则顺延，控制台打印实际端口） |
| 资源 | S9 静态壳 | **自洽拷贝**同构 fixture（非 symlink）；不破坏 `demos/ui` |

## 启动（Windows 优先）

在仓库根目录：

```bat
cd demos\desktop
start_desktop.bat
```

或：

```bat
cd demos\desktop
npm install --no-audit --no-fund --save-exact
npm start
```

- 首次会安装已钉死的 `electron@44.9.0`（精确版本，无 `^`）
- 窗口标题：`Vaelin UI 演示壳 · Desktop-S1 · DEMO · 非生产`
- 加载：内嵌 HTTP `http://127.0.0.1:8766/`（或顺延），**不用** `file://`
- 关闭窗口即停静态服
- 需要本机已装 **Node.js／npm**

macOS／Linux：本拍未提供启动脚本；当前以 Windows 为准。

## 遥测与隔离

主进程 **不** 调用 `crashReporter`、**不** 依赖 `electron-updater`。启动开关关闭后台联网、组件更新、域可靠性、Breakpad、同步与 Safe Browsing 上报。页面请求非 `127.0.0.1`／`localhost` 会被取消。Electron 用户数据落在本目录 `.electron-userdata/`（**不是** 任何 Hermes 目录）。

## 硬闸

零 Hermes／hooks／plugins／vault／SEALED · 不写 Hermes 用户目录 · 三模式仍灰态 · 无真后端／模型 API · 无 installer／Release／商店／自动更新 · 禁公网隧道 · **demo ≠ production** · **install ≠ enable**
