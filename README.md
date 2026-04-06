<!--
 *  =======================================================================
 *  ····Y88b···d88P················888b·····d888·d8b·······················
 *  ·····Y88b·d88P·················8888b···d8888·Y8P·······················
 *  ······Y88o88P··················88888b·d88888···························
 *  ·······Y888P··8888b···88888b···888Y88888P888·888·88888b·····d88b·······
 *  ········888······"88b·888·"88b·888·Y888P·888·888·888·"88b·d88P"88b·····
 *  ········888···d888888·888··888·888··Y8P··888·888·888··888·888··888·····
 *  ········888··888··888·888··888·888···"···888·888·888··888·Y88b·888·····
 *  ········888··"Y888888·888··888·888·······888·888·888··888··"Y88888·····
 *  ·······························································888·····
 *  ··························································Y8b·d88P·····
 *  ···························································"Y88P"······
 *  =======================================================================
 * 
 *  -----------------------------------------------------------------------
 * Author       : 焱铭
 * Date         : 2025-04-22 10:43:55 +0800
 * LastEditTime : 2025-05-06 14:41:13 +0800
 * Github       : https://github.com/YanMing-lxb/
 * FilePath     : /egasp/README.md
 * Description  : 
 *  -----------------------------------------------------------------------
 -->

# 乙二醇水溶液物性参数查询程序 | egasp (Ethylene Glycol Aqueous Solution Properties)

[![GitHub](https://img.shields.io/badge/Github-EGASP-000000.svg)](https://github.com/YanMing-lxb/egasp) [![License](https://img.shields.io/badge/license-GPLv3-aff)](https://www.latex-project.org/lppl/) ![OS](https://img.shields.io/badge/OS-Linux%2C%20Win%2C%20Mac-pink.svg) [![GitHub release](https://img.shields.io/github/release/YanMing-lxb/egasp.svg?color=blueviolet&label=version&style=popout)](https://github.com/YanMing-lxb/egasp/releases/latest) [![Last Commit](https://img.shields.io/github/last-commit/YanMing-lxb/egasp)](https://github.com/YanMing-lxb/egasp/zipball/master) [![Issues](https://img.shields.io/github/issues/YanMing-lxb/egasp)](https://github.com/YanMing-lxb/egasp/issues) [![PyPI version](https://img.shields.io/pypi/v/egasp.svg)](https://pypi.python.org/pypi/egasp/) [![PyPI Downloads](https://img.shields.io/pypi/dm/egasp.svg?label=PyPI%20downloads)](https://pypi.org/project/egasp/) ![GitHub repo size](https://img.shields.io/github/repo-size/YanMing-lxb/egasp)

## 安装

官方版本 egasp 发布在 [PyPI](https://pypi.org/project/egasp/) 上，并且可以通过 pip 包管理器从 PyPI 镜像轻松安装。

请注意，您必须使用 Python 3 版本 pip：

```
pip3 install egasp
```

## 多平台支持

EGASP 现在使用现代的 Excel Web Add-in，支持以下平台：

### Windows 平台
- 使用 Excel Web Add-in
- 支持 Excel 2016 及以上版本
- 无需 VBA 宏支持

### Web 平台
- 使用 Office.js 构建的 Web Add-in
- 支持 Excel for Web
- 无需安装，直接加载

## 安装说明

### 安装 Excel Web Add-in

1. **构建应用**
   ```bash
   python -m tools.app_builder
   ```

2. **运行配置脚本**
   - 运行 `dist/egasp-v*/configure_egasp_env.bat` 配置环境变量

3. **加载 Web Add-in**
   - 在 Excel 中打开'插入'选项卡
   - 点击'我的加载项' -> '管理我的加载项'
   - 点击'上传我的加载项'，选择 `dist/egasp-v*/manifest.xml` 文件
   - 加载项将出现在 Excel 功能区中

### 开发环境设置

1. **安装依赖**
   ```bash
   cd web_addin
   npm install
   ```

2. **构建 Web Add-in**
   ```bash
   cd web_addin
   npm run build
   ```

3. **启动开发服务器**
   ```bash
   cd web_addin
   npm run dev-server
   ```

## 跨平台测试

EGASP 提供了跨平台测试脚本，用于验证插件在不同平台上的功能：

```bash
# 运行跨平台测试
python tools/test_cross_platform.py

# 运行Windows平台测试
python tools/test_windows_addin.py

# 运行Mac平台测试
python tools/test_mac_addin.py

# 运行Web平台测试
python tools/test_web_addin.py
```


## 升级

```
pip3 install --upgrade egasp
```

## Excel Web Add-in 使用说明

### 使用方法

#### 1. 使用功能区按钮

在 Excel 功能区中找到 `EGASP` 选项卡，包含以下功能：

- **初始化 EGASP**：配置 EGASP 环境
- **物性参数查询**：打开任务窗格进行参数计算
- **清除缓存**：清除计算缓存
- **缓存状态**：查看缓存使用情况

#### 2. 使用自定义函数

在 Excel 单元格中直接输入函数，例如：

```excel
=EG_RHO("volume", 0.5, 25)  // 获取体积浓度 50%、温度 25°C 时的密度
=EG_MU("mass", 0.3, 10)   // 获取质量浓度 30%、温度 10°C 时的粘度
=EG_CP("volume", 0.6, 30)  // 获取体积浓度 60%、温度 30°C 时的比热容
=EG_K("volume", 0.4, 50)  // 获取体积浓度 40%、温度 50°C 时的导热系数
=EG_TF("mass", 0.7)  // 获取质量浓度 70% 时的冰点
=EG_TB("volume", 0.3)  // 获取体积浓度 30% 时的沸点
```

#### 3. 使用任务窗格

1. 点击功能区中的 'EGASP' 按钮打开任务窗格
2. 在任务窗格中输入以下参数：
   - 浓度类型：体积浓度或质量浓度
   - 浓度值：0.1-0.9
   - 温度：-35~125°C
   - 物性参数：密度、粘度、比热容、导热系数、冰点、沸点
3. 点击 '计算' 按钮查看结果

#### 4. 高级使用场景

##### 场景1：温度变化对物性的影响

```excel
// A列：温度值从-30到100，步长10
// B列：体积浓度50%时的密度变化
=EG_RHO("volume", 0.5, A2)

// C列：体积浓度50%时的粘度变化
=EG_MU("volume", 0.5, A2)
```

##### 场景2：浓度变化对冰点的影响

```excel
// A列：体积浓度从0.1到0.9，步长0.1
// B列：对应的冰点
=EG_TF("volume", A2)
```

##### 场景3：质量浓度与体积浓度转换

```excel
// A列：质量浓度
// B列：转换为体积浓度
=EG_VOL("mass", A2, 25)

// C列：转换回质量浓度（验证）
=EG_MASS("volume", B2, 25)
```

##### 场景4：综合热物性分析

```excel
// A列：温度
// B列：密度
=EG_RHO("volume", 0.5, A2)

// C列：比热容
=EG_CP("volume", 0.5, A2)

// D列：导热系数
=EG_K("volume", 0.5, A2)

// E列：粘度
=EG_MU("volume", 0.5, A2)
```

### 支持的函数

| 函数名 | 描述 | 参数 |
|-------|------|------|
| `EG_INITIALIZE` | 初始化 EGASP | 无 |
| `EG_PROPERTY` | 通用属性查询 | type, value, temp, prop |
| `EG_RHO` | 获取密度 | type, value, temp |
| `EG_MU` | 获取粘度 | type, value, temp |
| `EG_CP` | 获取比热容 | type, value, temp |
| `EG_K` | 获取导热系数 | type, value, temp |
| `EG_TF` | 获取冰点 | type, value |
| `EG_TB` | 获取沸点 | type, value |
| `EG_MASS` | 计算质量浓度 | type, value, temp |
| `EG_VOL` | 计算体积浓度 | type, value, temp |
| `EG_CLEAR_CACHE` | 清除缓存 | 无 |
| `EG_TOGGLE_CACHE` | 切换缓存状态 | enabled |
| `EG_CACHE_STATUS` | 获取缓存状态 | 无 |

### 参数说明

- **type**：浓度类型，支持 `volume`（体积浓度）或 `mass`（质量浓度）
- **value**：浓度值，范围 0.1-0.9
- **temp**：温度值，单位 °C，范围 -35~125
- **prop**：物性参数名称，支持：
  - `rho` 或 `density`：密度
  - `mu` 或 `viscosity`：粘度
  - `cp` 或 `specific_heat`：比热容
  - `k` 或 `thermal_conductivity`：导热系数
  - `freezing` 或 `freezing_point`：冰点
  - `boiling` 或 `boiling_point`：沸点
  - `mass` 或 `mass_concentration`：质量浓度
  - `volume` 或 `volume_concentration`：体积浓度

### 错误提示说明

- `#ERROR: 未找到EGASP可执行文件路径`：请先运行 EG_INITIALIZE 函数
- `#ERROR: 无效的浓度类型`：浓度类型必须是 volume 或 mass
- `#ERROR: 浓度值超出范围`：浓度值必须在 0.1-0.9 之间
- `#ERROR: 温度超出范围`：温度必须在 -35°C 到 125°C 之间
- `#ERROR: 无效的物性参数`：请检查物性参数名称是否正确

## 构建指南

### 构建完整应用

1. **安装依赖**
   ```bash
   uv install
   ```

2. **生成可执行文件**
   ```bash
   make pack
   ```

3. **构建完整应用包**
   ```bash
   python -m tools.app_builder
   ```

### 构建 Excel Web Add-in

1. **安装 Web Add-in 依赖**
   ```bash
   cd web_addin
   npm install
   ```

2. **构建 Web Add-in**
   ```bash
   cd web_addin
   npm run build
   ```

3. **构建完整插件包**
   ```bash
   python -m tools.build_addin
   ```

4. **输出产物**
   - `dist/egasp-vX.X.X/`：完整应用包
   - `dist/excel_addin/`：Excel Web Add-in 构建结果

## 性能优化

### 缓存机制

插件内置了高效的缓存系统，显著提高重复计算的性能：

- **缓存大小**：默认 1000 条记录
- **缓存命中**：相同参数的查询会直接返回缓存结果
- **缓存淘汰**：使用 FIFO 策略自动淘汰旧记录

### 性能统计

通过功能区中的 `性能统计` 按钮可以查看缓存状态和使用情况。

## 常见问题

### 1. EGASP 功能区不显示
- 检查宏是否启用
- 重启 Excel/WPS
- 重新导入 `EGASP_Integration.bas` 文件

### 2. 函数返回 #NO_EXE_FOUND
- 运行 `设置` 按钮配置 EGASP 可执行文件路径
- 确保 `egasp.exe` 已正确安装

### 3. 函数返回 #EXEC_ERROR
- 检查输入参数是否正确
- 确保浓度和温度在有效范围内

### 4. Excel/WPS 崩溃或无响应
- 尝试清除缓存
- 检查 EGASP 可执行文件是否为最新版本
- 减少批量处理的数据量

## 未来计划

- [X] 打包成独立可执行程序
- [X] 支持 Excel/WPS 调用
- [X] 改进 Excel 加载项的计算速度（已通过缓存机制实现）
- [ ] 添加单位转换工具
- [ ] 支持更多物性参数

## 来源

https://www.glycolsales.com.au/dowtherm/dowtherm-sr-1/
