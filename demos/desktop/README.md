# Vaelin UI 演示壳 · Desktop UI-only 加深（DEMO · 非生产）

> **公开仓桌面演示窗** · 薄 Electron 壳 + fixture 静态资源 · 纯假数据  
> 相对 **Desktop Hermes-PUB／PR#12**（tip `ef0a164`）增量：**UI-only 加深**（节点门旁路屏 `screen-nodegate` · 假数据可视化 · 三模式灰态轻打磨）  
> **签 ≠ 启用** · **demo ≠ production** · **install ≠ enable** · **PUB ≠ 生产 enable** · **8766 ≠ 生产 Hermes**  
> **不是** 生产 Hermes 启用 · **不是** SQLite／tool_gate 旁路接入生产 · **不是** installer／商店／自动更新

## 演示 ≠ 生产 · install ≠ enable · PUB ≠ 生产 enable

- 这是 **DEMO／非生产** 独立桌面窗，**不是** 生产 Vaelin，**不是** 已启用生产 Hermes 的安装包
- **签 ≠ 启用**：勾签／合入本加深 **不等于** 启用生产 Hermes
- **install ≠ enable**：本目录可本地 `npm install` Electron，**不等于** 生产 enable／vault 接入
- **PUB ≠ 生产 enable**：公开仓有 UI-only 加深演示面 **不等于** 本机／生产 Hermes 已启用
- **8766 ≠ 生产 Hermes**：本窗＠`127.0.0.1:8766`＝演示壳；**不是** `%LocalAppData%\hermes`
- 假数据 fixture／`data/nodegate_fixture.json`；不接 vault／生产 Hermes／SEALED／plugins／config／tool_gate
- 节点门屏只展示 **假数据** 旁路叙事（`_nodegate_sandbox` 逻辑标签）；**不迁**沙箱整树入仓
- 三模式（氧气／凯撒／玥）仍为壳内 **静态灰态**（无真接线）
- 未做代码签名、商店上架、自动更新、Program Files 安装、installer／Release 资产
- **禁公网隧道** · 静态服只绑 `127.0.0.1` · **零会话**

## 与 `demos/ui` 的关系

| | `demos/ui`（浏览器） | 本目录 `demos/desktop` |
|---|---|---|
| 打开 | `start_demo.bat` → 浏览器 `http://127.0.0.1:8765/` | `start_desktop.bat` → **独立 Electron 窗** |
| 端口 | 8765 | **8766**（占用则顺延，控制台打印实际端口） |
| 资源 | Web 静态壳 | **自洽拷贝**同构 fixture（非 symlink）；不破坏 `demos/ui` |

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
- `HERMES_HOME` 默认指向本目录 **`_hermes_sandbox_stub/`**（演示 stub；**禁止**指向 `%LocalAppData%\hermes`）
- 窗口标题含 **Desktop-S3**／DEMO／非生产；硬闸含 **沙箱 ≠ 生产**／**PUB ≠ 生产 enable**／**UI-only**
- 导航含 **节点门**（`screen-nodegate`）；脚本 `js/desktop_nodegate_viz.js`＋`data/nodegate_fixture.json`
- 加载：内嵌 HTTP `http://127.0.0.1:8766/`（或顺延），**不用** `file://`
- 关闭窗口即停静态服
- **F1**／**?**：桌面键位帮助；**Ctrl+Shift+A**：硬闸／About
- 窗口位置／尺寸写入本目录 `.electron-userdata/window-bounds.json`（**不是** Hermes 生产目录）
- 需要本机已装 **Node.js／npm**

macOS／Linux：本拍未提供启动脚本；当前以 Windows 为准。

### 可选轻量托盘（默认关 · 继承 S2）

```bat
cd demos\desktop
set DESKTOP_S2_TRAY=1
start_desktop.bat
```

或：`npx electron . --tray`  
托盘提示含「演示／非生产」；菜单可显示窗／退出演示。**非常驻生产级服务**；关掉即停服。默认不启托盘。

## Hermes 沙箱演示 stub（公开面）

| 项 | 值 |
|---|---|
| 方案面 | **H-SBX-A 可公开 stub**（相对 PR#12／Hermes-PUB） |
| stub 目录 | `demos/desktop/_hermes_sandbox_stub/`（`SANDBOX_MARKER.json`＋假 `status.json`） |
| `HERMES_HOME` | 启动校验必须落在该相对 stub；**拒** `%LocalAppData%\hermes` |
| 生产 Hermes | **零改**（本演示不读写生产 hooks／config／vault／SEALED／scheduler） |
| 端口 | 默认 **8766**＠`127.0.0.1`；**8766 ≠ 生产 Hermes** |
| 脚本 | `js/desktop_hermes_sandbox.js`（读本地 `/sandbox-hermes-status.json`；**不**接生产 IPC） |

## UI-only 加深（本 PR · Desktop-UiDeepen-PUB）

| 项 | 值 |
|---|---|
| 代号 | **Desktop-UiDeepen-PUB** |
| 基线 | 公开 `main` tip `ef0a164`（PR#12 Hermes-PUB） |
| 增量 | `screen-nodegate` · `js/desktop_nodegate_viz.js` · `data/nodegate_fixture.json` · 相关 index／demo.js／css／fixture／README |
| 口径 | **UI-only** · 假数据 · **零会话** · **零碰生产 Hermes** · PUB ≠ 生产 enable |
| OUT | 整树 `_hermes_desktop_sandbox`／`_nodegate_sandbox` 不入仓；不改 `demos/ui`；不刷树；默不合入 |

## 自测（DOM selftest）

```bat
cd demos\desktop
run_selftest.bat
```

探针（失败非零退出）：

1. 窗口标题含 **Desktop-S3**／演示／DEMO／非生产
2. 壳内可见 **签 ≠ 启用**、非生产／演示、**8766 ≠ 生产 Hermes**、沙箱口径
3. `[id^="screen-"]` ≥ 5（含 `screen-nodegate`）
4. 默认端口逻辑仍从 **8766** 起；HTTP 可达
5. userData 仍在本目录 `.electron-userdata/`（不含生产 hermes 路径）
6. `HERMES_HOME` 为 `_hermes_sandbox_stub`；marker 存在；`productionHermesTouched=false`
7. `js/desktop_nodegate_viz.js` 与 `data/nodegate_fixture.json` 存在
8. 写出 `selftest-out.json`（已 gitignore）；`selftest_check.js` 校验

## 遥测与隔离

主进程 **不** 调用 `crashReporter`、**不** 依赖 `electron-updater`。启动开关关闭后台联网相关上报。页面请求非 `127.0.0.1`／`localhost` 会被取消。Electron 用户数据落在本目录 `.electron-userdata/`。

## 回滚口径（公开面）

- 关掉桌面窗后，可还原本目录至上一公开面（Hermes-PUB／PR#12 tip `ef0a164`），或另开 revert PR。
- **不要**为回退去改生产 Hermes／vault／tool_gate／CEV。
- `selftest-out*.json`／`node_modules`／`.electron-userdata`／`window-bounds.json` **不入仓**。

## 硬闸

零改生产 Hermes／hooks／plugins／vault／SEALED／config／tool_gate／deploy · 不写 Hermes 生产用户目录 · 三模式仍灰态 · 无真后端／模型 API · 无 installer／Release／商店／自动更新 · 禁公网隧道 · **签 ≠ 启用** · **demo ≠ production** · **install ≠ enable** · **PUB ≠ 生产 enable** · **8766 ≠ 生产 Hermes** · **零会话** · 默认端口 **8766** · 托盘默认关 · 默只开 PR · 合须另批