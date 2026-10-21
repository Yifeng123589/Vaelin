# Vaelin UI 演示壳 · Desktop-S2（DEMO · 非生产）

> **公开仓桌面演示窗** · 薄 Electron 壳 + 自洽拷贝的 fixture 静态资源 · 纯假数据 · **零接 Hermes**  
> **Desktop-S2**＝相对 Desktop-S1 的加深面：自测稳定性／可选轻量托盘／`run_selftest`／文档短注  
> **demo ≠ production** · **install ≠ enable** · 不是可分发安装包／不是已上架产品

## 演示 ≠ 生产

- 这是 **DEMO／非生产** 独立桌面窗，**不是** 生产 Vaelin，**不是** 已接 Hermes 的安装包
- **install ≠ enable**：本目录可本地 `npm install` Electron，**不等于** 启用生产／Hermes／vault
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
- 窗口标题：`Vaelin UI 演示壳 · Desktop-S2 · DEMO · 非生产`
- 加载：内嵌 HTTP `http://127.0.0.1:8766/`（或顺延），**不用** `file://`
- 关闭窗口即停静态服
- 脚本会打印当前路径、默认端口、缺依赖提示
- 需要本机已装 **Node.js／npm**

macOS／Linux：本拍未提供启动脚本；当前以 Windows 为准。

### 可选轻量托盘（默认关）

```bat
cd demos\desktop
set DESKTOP_S2_TRAY=1
start_desktop.bat
```

或：`npx electron . --tray`  
托盘提示含「演示／非生产」；菜单可显示窗／退出演示。**非常驻生产级服务**；关掉即停服。默认不启托盘。图标：`assets/tray-demo.png`（演示 only）。

## Desktop-S2 自测（DOM selftest）

```bat
cd demos\desktop
run_selftest.bat
```

探针（失败非零退出）：

1. 窗口标题含「演示／DEMO／非生产」
2. 壳内正文可见非生产／演示／零 Hermes 声明
3. `[id^="screen-"]` ≥ 5
4. 默认端口逻辑仍从 **8766** 起（未改回 8765）；HTTP 可达
5. 写出 `selftest-out.json`（已 gitignore）；`selftest_check.js` 校验

环境变量：`DESKTOP_S2_SELFTEST=1` · `DESKTOP_S2_SELFTEST_OUT=...`（兼容旧 `DESKTOP_S1_SELFTEST*`）

## 遥测与隔离

主进程 **不** 调用 `crashReporter`、**不** 依赖 `electron-updater`。启动开关关闭后台联网、组件更新、域可靠性、Breakpad、同步与 Safe Browsing 上报。页面请求非 `127.0.0.1`／`localhost` 会被取消。Electron 用户数据落在本目录 `.electron-userdata/`（**不是** 任何 Hermes 目录）。

## 回滚口径（公开面）

- 关掉桌面窗后，可还原本目录至上一公开面（Desktop-S1／合入前 tip），或另开 revert PR。
- **不要**为回退去改 Hermes／vault／生产路径。
- `selftest-out*.json`／`node_modules`／`.electron-userdata` **不入仓**。

## 硬闸

零 Hermes／hooks／plugins／vault／SEALED · 不写 Hermes 用户目录 · 三模式仍灰态 · 无真后端／模型 API · 无 installer／Release／商店／自动更新 · 禁公网隧道 · **demo ≠ production** · **install ≠ enable** · 默认端口 **8766** · 托盘默认关
