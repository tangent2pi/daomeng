# 到梦空间自动化脚本 - AI 代码助手指南

## 项目概述

这是一个基于 Android UI 自动化的学分颁发系统，通过 ADB 和 uiautomator2 控制移动设备，自动为学生批量颁发"到梦空间"APP 的活动学分。

**核心价值链**: Excel 名单 → 学号验证 → SQLite 持久化 → UI 自动导航 → 学分颁发 → 结果跟踪

## 架构设计

### 分层职责（严格遵守单一职责原则）

```
DM.py (入口点)
  └→ cli.py (命令行解析与配置管理)
      └→ automation_app.py (任务编排与进度管理)
          ├→ file_manager.py (数据验证、SQLite 操作、Excel I/O)
          └→ device_controller.py (ADB 连接、UI 导航、学分颁发)
```

- **`file_manager.py`**: 负责所有数据操作。读取 Excel → 学号提取与验证 → 交互式用户确认 → SQLite 持久化 → 结果导出。使用 `pandas` 和 `sqlite3`。
- **`device_controller.py`**: 封装设备交互。管理 ADB 连接、uiautomator2 会话、UI 元素定位（通过 `selectors.py`）、导航状态机、学分颁发逻辑。
- **`automation_app.py`**: 任务协调器。按分值分组处理学生、管理 `rich` 进度条、协调 file_manager 与 device_controller、捕获顶层异常。
- **`cli.py`**: 参数解析与配置序列化。支持任务恢复（`-r`）、无线调试配对（`-p`）、账号自动登录（`-u`）、易班ID映射（`-yb`）。

### 关键数据流

1. **学号验证流程**（`file_manager.py` 约 400-600 行）:
   - 使用正则 `r'(?<!\d)\d{11}(?!\d)'` 提取 11 位学号
   - **易班ID映射**（新功能）: 如果发分名单缺少学号列但有易班ID列，通过 `-yb` 参数指定的CSV文件进行映射
     - 映射文件需包含: `姓名`, `学号`, `易班ID` 三列
     - 映射时同时验证易班ID和姓名，确保数据准确性
     - 无法映射时使用默认学号 `1000000000`
   - 与录取名单（分值 0）交叉验证姓名
   - **交互式确认**: 无效学号显示富文本表格，用户选择处理方式（全拒绝/自动映射/手动输入）
   - 姓名不匹配同样需要用户确认后才继续

2. **任务恢复机制**:
   - 每次运行在 `<活动名>-<时间戳>/` 目录保存 `config.json` 和 `students.db`
   - 使用 `-r` 参数指定目录路径即可从数据库恢复未处理学生，跳过 Excel 读取

3. **UI 导航状态机**（`device_controller.py` `navigation()` 方法）:
   - 通过 `_get_current()` 识别当前界面（登录/首页/活动管理/学分管理/发分界面）
   - 自动处理登录失效、应用重启、多次返回后重置
   - 特殊逻辑: 颁发前必须验证 `self.score` 与目标分值一致

## 开发约定

### 日志规范
- 使用 `self._logger` 而非 `print()`（除 `cli.py` 的启动横幅）
- 用户交互信息用 `rich.Console()` 渲染表格/提示
- 日志级别: DEBUG=调试跟踪, INFO=关键步骤, WARNING=可恢复异常, ERROR=失败

### 错误处理模式
- 数据验证错误 → 记录到数据库（状态列标记"学号错误"/"姓名错误"/"未报名"），继续执行
- UI 元素未找到 → 自动重试 1 次（`device_controller.award_points()` 的 `c` 计数器）
- 导航失败 > 5 次 → 暂停并请求人工干预（`Prompt.ask()`）

### 配置管理
- 配置类: `AutomationConfig` (dataclass，单一数据源)
- 命令行参数与恢复配置冲突时，命令行优先（例外: 账号信息）
- ADB 路径通过环境变量 `ADBUTILS_ADB_PATH` 指定为 `platform-tools/adb.exe`

### UI 选择器维护（`selectors.py`）
- 所有选择器集中定义在 `SELECTORS` 字典
- 键名使用中文描述功能，值是 uiautomator2 的 `resourceId`/`text`/`index`
- **重要**: APP 更新后选择器可能失效，需用 `uiautomatorviewer` 重新获取

### Excel 文件约定
- 录取名单（分值 0）必须包含: `学号`, `姓名` 列
- 发分名单（分值 > 0）必须包含: `姓名` 列，`学号` 列可选（可通过易班ID映射）
  - 如有 `学号` 列：直接使用学号
  - 如无 `学号` 列但有 `易班ID` 列：需提供 `-yb` 参数指定易班映射CSV文件
  - 可选列: `院系`, `专业`, `班级`
- 附加名单必须包含: `学号`, `姓名`, `分值` 列（支持 `m`/`max` 标记使用最大分值）
- 易班ID映射文件（CSV格式）必须包含: `姓名`, `学号`, `易班ID` 列
- 活动名称从录取名单第 2 行的"活动名称"列读取

## 常见任务

### 添加新的 UI 导航路径
1. 在 `selectors.py` 添加新界面的选择器
2. 在 `device_controller._get_current()` 添加界面识别逻辑
3. 在 `navigation()` 的状态机中添加导航分支

### 修改学号验证规则
编辑 `file_manager._extract_student_id()`，注意保持 11 位验证逻辑和正则提取的兼容性。

### 调试设备连接问题
1. 确保 `platform-tools/adb.exe` 存在
2. 首次连接或异常时使用 `-i` 参数初始化 uiautomator2
3. 无线调试用 `-p IP:PORT CODE` 配对后，再用 `-d IP:PORT` 连接
4. 检查 `automation.log` 中的 ADB 连接日志

### 测试与验证
- 使用小数据集（3-5 人）测试完整流程
- 验证 `students.db` 的状态更新（用 SQLite 工具检查）
- 检查输出目录的 `<活动名>.xlsx` 结果文件

## 技术栈
- **UI 自动化**: uiautomator2 (Android)
- **数据处理**: pandas, openpyxl, sqlite3
- **CLI/TUI**: argparse, rich (进度条/表格/日志)
- **Python 版本**: 3.12+（使用 dataclass, typing, match-case 等特性）

## 注意事项
- **并发安全**: 不支持多设备并发（全局状态 `self.score`）
- **设备要求**: 需启用开发者选项、USB 调试或无线调试
- **幂等性**: 重复运行会覆盖相同学号的记录（取最大分值）
- **清理机制**: 任务完成后自动删除 `.db`/`.db-wal`/`.db-shm`/`config.json`，仅保留 Excel 结果
