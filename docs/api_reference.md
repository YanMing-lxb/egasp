# EGASP API 参考

> 版本 0.3.0 · 最后更新 2026-09-29

本页是 EGASP 公开 API 的完整参考。库从 v0.3.0 起将 EGASP 分为两个并行层级：

- **高性能内核层** — `compile_mixture()` + `CompiledEGMixture`，面向热网络求解器 / 批量计算
- **legacy 兼容层** — `EGASP` 类 / `prop()` / `props()` / `fb_props()`，面向 CLI / Excel / 脚本

两个层级数值严格一致（max rel diff ≤ 4.5e-16）。

---

## 1. 安装与导入

```bash
pip install egasp
# 或通过 uv（推荐）
uv add egasp
```

```python
import egasp
print(egasp.__version__)  # "0.3.0"
```

### 可用属性

```python
egasp.__version__                   # str: "0.3.0"
egasp.compile_mixture(c)            # LRU 入口
egasp.CompiledEGMixture             # dataclass
egasp.PropertyWorkspace            # 持久容器
egasp.EGASP                         # legacy 主类
egasp.prop(T, c, key)               # legacy 单属性快捷
egasp.props(T, type, value)         # legacy 全属性快捷
egasp.fb_props(value, type)         # 冰点/沸点查询
egasp.concentration_type_to_chinese # 静态工具
egasp.main()                        # CLI 入口（lazy import rich）
# 异常
egasp.EGASPError / PropertyOutOfRangeError / InvalidInputError / ...
```

---

## 2. `compile_mixture()` — 编译入口

```python
from egasp import compile_mixture

compile_mixture(concentration: float) -> CompiledEGMixture
```

### 参数

| 参数 | 类型 | 范围 | 说明 |
|---|---|---|---|
| `concentration` | float | 0.1 ≤ c ≤ 0.9 | **体积浓度**（如 0.5 = 50%） |

### 返回

`CompiledEGMixture` 实例（构造过程可能耗时 ~1-5 ms），**相同 concentration 重复调用命中 LRU**（@lru_cache maxsize=32）。

### 异常

| 异常 | 条件 |
|---|---|
| `PropertyOutOfRangeError` | concentration 超出 [0.1, 0.9] |
| `CompilationError` | 数据库节点间距为零 / 有效区间不连续 / h 非单调 |
| `MissingPropertyDataError` | 指定浓度下某属性无有效数据 |

### 示例

```python
cm050 = compile_mixture(0.5)          # 节点浓度，直接取列，零插值
cm033 = compile_mixture(0.33)         # 非节点值，沿浓度双线性插值
same  = compile_mixture(0.5) is cm050 # True — LRU 命中
```

---

## 3. `CompiledEGMixture` — 物性内核

固定浓度乙二醇水溶液的预编译物性表 + 融合求值器。使用 `compile_mixture()` 构造。

### 只读属性

| 属性 | 类型 | 说明 |
|---|---|---|
| `conc` | float | 实际编译时使用的浓度（节点时 = 节点值，非节点时 = 插值值） |
| `volume_fraction` | float | 体积浓度（与 `conc` 同义） |
| `mass_fraction` | float \| None | 质量浓度，通过 fb 表插值得到 |
| `freezing_point` | float \| None | 冰点 °C |
| `boiling_point` | float \| None | 沸点 °C |
| `Tmin` | float | 五属性**公共有效域**最低温度（节点值） |
| `Tmax` | float | 五属性**公共有效域**最高温度（节点值） |
| `validity` | bool | 整个 [Tmin, Tmax] 内五属性是否均无 NaN |
| `hmin` | float | 焓值有效下界（J/kg） |
| `hmax` | float | 焓值有效上界（J/kg） |
| `h_mono` | bool | 编译阶段验证：焓值是否严格单调递增 |
| `table` | ndarray | **只读**，形状 `(5, 33)`，五属性温度节点值 |
| `dtable` | ndarray | **只读**，形状 `(5, 33)`，区间内常数导数 |
| `h_nodes` | ndarray | **只读**，形状 `(33,)`，焓值节点表 |
| `valid_start_idx` | ndarray | 形状 `(5,)`，每属性第一个有效温度节点索引 |
| `valid_end_idx` | ndarray | 形状 `(5,)`，每属性最后一个有效温度节点索引 |
| `h_valid_idx` | ndarray | 焓值有效切片索引（供反解使用） |

### `evaluate(T)` — 融合批量求值

```python
evaluate(T: float | np.ndarray) -> np.ndarray
```

同时返回五属性，**顺序固定 `[rho, cp, h, k, mu]`**。

| 输入 T | 返回形状 | 说明 |
|---|---|---|
| scalar float | `(5,)` | 1D ndarray |
| 1D ndarray of shape `(N,)` | `(5, N)` | 2D ndarray |

**公共有效域检查**：T 必须在 `[Tmin, Tmax]` 内，否则 raise `PropertyOutOfRangeError`。
**NaN/Inf 拒绝**：T 含 NaN/inf raise `InvalidInputError`。

#### 示例

```python
cm = compile_mixture(0.5)

# 标量
v = cm.evaluate(25.0)
# array([1071.11, 3300.00, 191045.00, 0.37, 0.00339])
#        rho     cp       h           k     mu

# 批量
temps = np.array([0.0, 25.0, 50.0, 100.0])
V = cm.evaluate(temps)      # shape (5, 4)
rho, cp, h, k, mu = V[0], V[1], V[2], V[3], V[4]
```

### `evaluate_into(T, out)` — 原地写入

```python
evaluate_into(T: np.ndarray, out: np.ndarray) -> None
```

预分配输出 ndarray `out.shape == (5, N)`，适合固定网络规模（如 PHEx/MS-FHTN）迭代时重复调用以避免每轮 new 数组。

```python
out = np.empty((5, 5000), dtype=np.float64)
for iteration in range(10000):
    cm.evaluate_into(temps, out)  # 零堆分配
```

### 单属性快捷方法

| 方法 | 签名 | 返回 |
|---|---|---|
| `rho(T)` | `T: float \| ndarray` | float 或 ndarray — 密度 kg/m³ |
| `cp(T)` | 同上 | 比热容 J/kg·K |
| `h(T)` / `h_from_T(T)` | 同上 | 焓 J/kg（相对值，各浓度最低温度为 0） |
| `k(T)` | 同上 | 导热系数 W/m·K |
| `mu(T)` | 同上 | 动力粘度 **Pa·s**（注意：旧版内部 mPa·s） |

单属性方法检查**该属性自身独立有效域**（可能比公共域更广）。

### `mu_into(T, out)` — 壁面粘度 fast path

```python
mu_into(T: np.ndarray, out: np.ndarray) -> None
```

仅计算 mu 的原地写入，跳过其他四属性的 gather。壁面粘度计算专用。

### 焓反解 `temperature_from_h(h)`

```python
temperature_from_h(h: float | np.ndarray) -> float | np.ndarray
```

固定浓度下 `h → T` 安全反解。
- h 在 `[hmin, hmax]` 外 → `PropertyOutOfRangeError`
- h 含 NaN/Inf → `InvalidInputError`
- 编译阶段已验证 h 严格单调 → O(log n) searchsorted + 线性插值

```python
T = cm.temperature_from_h(191045.0)   # ≈ 25.0 (°C) 精确回解
```

### 导数方法

| 方法 | 含义 |
|---|---|
| `drho_dT(T)` | dρ/dT — 温度对密度的常数导数（区间内） |
| `dcp_dT(T)` | dcp/dT |
| `dh_dT(T)` | dh/dT（legacy-linear 区间内 = 平均 cp） |
| `dk_dT(T)` | dk/dT |
| `dmu_dT(T)` | dμ/dT |

### `PropertyWorkspace` 容器

```python
ws = cm.make_workspace(n_edges=5000)   # 预分配
cm.update_into(T, ws)                  # 原地更新所有字段
# ws.rho, ws.cp, ws.h, ws.k, ws.mu  ← 同步更新
# ws.T, ws.idx, ws.w                ← 中间状态可复用
```

等价 API：`ws.update(cm, T)`。

---

## 4. `EGASP` — legacy 兼容主类

```python
from egasp import EGASP
eg = EGASP()
```

### `prop(temp, conc, egp_key)` — 单属性查询

```python
eg.prop(temp: float | np.ndarray, conc: float, egp_key: str) -> float | np.ndarray
```

**内部完全委托** `compile_mixture(conc)`。

| egp_key | 单位 | 说明 |
|---|---|---|
| `"rho"` / `"density"` | kg/m³ | 密度 |
| `"cp"` / `"specific_heat"` | J/kg·K | 比热容 |
| `"h"` / `"enthalpy"` | J/kg | 焓（相对值） |
| `"k"` / `"thermal_conductivity"` | W/m·K | 导热系数 |
| `"mu"` / `"viscosity"` | **Pa·s** | 动力粘度 |

### `props(query_temp, query_type, query_value)` — 全属性查询

```python
eg.props(
    query_temp: float,
    query_type: str = "volume",      # "volume"/"v" 或 "mass"/"m"
    query_value: float = 0.5,
) -> tuple[Any, ...]
```

返回 9 元组：

```
(mass, volume, freezing, boiling, rho, cp, k, mu, h)
```

| 位置 | 字段 | 类型 | 说明 |
|---|---|---|---|
| 0 | mass | float \| None | 质量浓度 |
| 1 | volume | float \| None | 体积浓度 |
| 2 | freezing | float \| None | 冰点 °C |
| 3 | boiling | float \| None | 沸点 °C |
| 4 | rho | float | kg/m³ |
| 5 | cp | float | J/kg·K |
| 6 | k | float | W/m·K |
| 7 | mu | float | **Pa·s** |
| 8 | h | float | J/kg |

### `fb_props(query, query_type)` — 冰点沸点查询

```python
eg.fb_props(query: float, query_type: str = "volume") \
    -> tuple[float | None, float | None, float | None, float | None]
# 返回 (mass, volume, freezing, boiling)
```

**保持 legacy 插值路径**（冰点沸点数据存在非单调性，不走 compiled 内核）。内部 bisect + 线性插值，exact hit 优先。

### 静态工具

```python
EGASP.concentration_type_to_chinese(concentration_type: str) -> str
# "volume" → "体积浓度"
# "mass"   → "质量浓度"
```

---

## 5. 异常体系

```
Exception
 └── EGASPError
      ├── PropertyOutOfRangeError(query, lo, hi, param)
      ├── InvalidInputError(message)
      ├── MissingPropertyDataError(concentration, message)
      └── CompilationError(message)
```

### `PropertyOutOfRangeError`

**属性**：`query: float`, `lo: float`, `hi: float`, `param: str`（如 `"温度"` / `"浓度"` / `"焓"`）

**典型场景**：
- `evaluate(T)` 时 T < Tmin 或 T > Tmax
- `compile_mixture(c)` 时 c < 0.1 或 c > 0.9
- `temperature_from_h(h)` 时 h < hmin 或 h > hmax

### `InvalidInputError`

输入含 NaN / inf / -inf / 非法浓度类型 / 非法属性 key。

### `MissingPropertyDataError`

数据库节点缺失指定属性数据。构造时抛出，通常意味着浓度超出数据覆盖。

### `CompilationError`

编译阶段致命错误（浓度节点零间距、h 非单调、有效区间不连续）。正常数据不会触发。

---

## 6. 数据边界

### 温度

- 数据库节点：`[-35, -30, -25, ..., 125]`（步长 5°C，共 33 个节点）
- 浓度 0.3：公共有效域 **0°C ~ 125°C**（rho 在低温端缺失）
- 浓度 0.5：公共有效域 **-35°C ~ 125°C**（全属性覆盖）

### 浓度

- 节点：`[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]`
- 非节点值：双线性插值
- 超出 raise `PropertyOutOfRangeError`

### 属性表轴

```
_PROPERTY_TABLE shape = (33, 9, 5)
        axis=0 → 温度节点索引 0..32
        axis=1 → 浓度节点索引 0..8
        axis=2 → 属性 [rho, cp, h, k, mu] 索引 0..4
```

### 单位

| 属性 | 单位 | 备注 |
|---|---|---|
| rho | kg/m³ | — |
| cp | J/kg·K | — |
| h | J/kg | 相对值，各浓度最低有效温度处为 0 |
| k | W/m·K | — |
| mu | **Pa·s** | legacy 内部已 /1000（原 mPa·s） |

---

## 7. 快速上手

### 7.1 CLI（命令行）

```bash
# 非交互（推荐）
python -m egasp -qv 0.5 25

# 多温度批量
python -m egasp -qv 0.5 20 30 40 50

# 交互式
python -m egasp
```

### 7.2 Python 批量计算

```python
import numpy as np
from egasp import compile_mixture

cm = compile_mixture(0.5)
temps = np.linspace(-30, 120, 1000)

V = cm.evaluate(temps)          # (5, 1000) 一次拿到五属性
rho, cp, h, k, mu = V[0], V[1], V[2], V[3], V[4]

# 焓反解
T_back = cm.temperature_from_h(h[500])  # ≈ temps[500]

# 热网络求解器：预分配 + 原地写入
ws = cm.make_workspace(1000)
for iter in range(10000):
    cm.update_into(T_iter, ws)   # ws.rho / ws.h / ... 原地更新
```

### 7.3 Legacy 兼容

```python
import egasp

eg = egasp.EGASP()
rho = eg.prop(25.0, 0.5, "rho")
rho_arr = eg.prop(np.array([20, 30, 40]), 0.5, "rho")
mass, vol, freez, boil, rho, cp, k, mu, h = eg.props(25.0, "volume", 0.5)
```

---

## 8. 性能参考

| 场景 | 耗时 | 备注 |
|---|---|---|
| `import egasp`（核心） | **< 10 ms** | lazy CLI import |
| `compile_mixture(0.5)` 首次 | ~2-5 ms | 含数组构造 |
| `compile_mixture(0.5)` 再次 | **< 1 μs** | LRU 命中 |
| `evaluate(5000 温度点)` × 100 次 | **0.26 ms avg** | 含 idx/w 计算 + 广播 |
| `evaluate_into(5000, 5×5000_out)` × 100 | 同上 | 零堆分配 |

> 基准测试使用 pytest-benchmark，实测环境 Python 3.13 + NumPy 最新 + Windows。

---

*文档结束 — 2026-09-29*
