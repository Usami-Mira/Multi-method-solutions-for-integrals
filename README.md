# Multi-Method Calculus Solver

A **Planner → Builder × K → Evaluator** agent system that solves calculus problems using multiple distinct strategies, verified by SymPy. Built for `qwen-plus` via DashScope (any OpenAI-compatible endpoint works).

> 核心理念：LLM 不擅长精确计算，但擅长策略与模式识别。把符号运算交给 SymPy，让 LLM 专注「选方法 + 拆步骤 + 解释」。

---

## 1. Architecture

```
                 ┌──────────────────────────────────────────┐
                 │  外层循环 outer loop (≤ max_outer_loops) │
                 │  ┌────────────────────────────────────┐  │
 Problem ───────▶│  │  Planner (T=0.9)                   │  │
                 │  │    → K diverse strategies          │  │
                 │  └────────────────────────────────────┘  │
                 │                  │                       │
                 │                  ▼                       │
                 │  ┌────────────────────────────────────┐  │
                 │  │  Builder × K (T=0.2, 并行)          │  │
                 │  │    每个 Builder 跑 ReAct 循环：      │  │
                 │  │      6–12 轮 LLM 调用，每轮决策      │  │
                 │  │      think | tool | finish          │  │
                 │  │    SymPy 执行所有符号运算            │  │
                 │  │    自检：求导/积分互逆校验           │  │
                 │  └────────────────────────────────────┘  │
                 │                  │                       │
                 │                  ▼                       │
                 │  ┌────────────────────────────────────┐  │
                 │  │  Evaluator (T=0.0)                 │  │
                 │  │    五级级联校验：                    │  │
                 │  │      L1 字符串归一                  │  │
                 │  │      L2 符号化简                    │  │
                 │  │      L3 类型专用（积分比导数）       │  │
                 │  │      L4 数值采样（30 点）           │  │
                 │  │      L5 LLM 仲裁（仅当 L1-L4 不确定）│  │
                 │  └────────────────────────────────────┘  │
                 │                  │                       │
                 │  is_correct? ────┴── 否 ──┐              │
                 │      │                    │              │
                 │      是                   ▼              │
                 │      │      记录 failed_strategies        │
                 │      │      → 进入下一轮（带失败提示）    │
                 └──────┼─────────────────────────────────────┘
                        ▼
                  EvalResult + 完整 trace
```

**关键设计：Builder ↔ Evaluator 循环**——若 Evaluator 判错，自动 replan 并重跑 K 个 Builder，最多 `max_outer_loops` 轮。

---

## 2. Tech Stack

| 维度 | 选型 |
|---|---|
| Python | ≥ 3.10 |
| LLM | `openai` SDK 调 DashScope OpenAI-compatible 端点（`qwen-plus`） |
| 数据 | `pandas`, `pyarrow`（parquet） |
| 符号引擎 | `sympy` + `latex2sympy2` |
| 异步 | `asyncio`, `aiohttp` |
| 配置 | `yaml` + `pydantic` |
| 测试 | `pytest`, `pytest-asyncio` |
| 进度条 | `tqdm` |

---

## 3. Setup

### 方案 A：标准 venv

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env       # 然后编辑 .env，填入 DASHSCOPE_API_KEY

# Linux / Mac
python3.10 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

### 方案 B：uv（更快）

```bash
uv venv --python 3.10
source .venv/bin/activate    # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

### 配置 API Key

编辑 `.env`：
```
DASHSCOPE_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

如需改用其他模型（如 `qwen-max`、`qwen-turbo`），改 `configs/model.yaml` 的 `model_id`。

---

## 4. Usage

### Step 1 — 探查数据（必做）

```bash
python scripts/inspect_parquet.py data/raw/question-v1.parquet
```
输出 `data/processed/_schema_report.json`，包含每列的 dtype、unique 数、样本值，方便确认自动列名映射是否正确。

### Step 2 — 加载 + 过滤

```bash
python -c "from calc_solver.data.loader import load_parquet; load_parquet('data/raw/question-v1.parquet')"
```
输出 `data/processed/problems.jsonl`（通过过滤的题）和 `_load_report.json`（拒收原因统计）。

### Step 3 — 端到端跑题

```bash
# 跑前 20 题快速验证
python scripts/run_batch.py --parquet data/raw/question-v1.parquet --K 3 --max-rows 20

# 跑全集
python scripts/run_batch.py --parquet data/raw/question-v1.parquet --K 3
```

### Step 4 — 看结果

```bash
python scripts/analyze_results.py logs/<run_id>
```
生成 `summary.md`：准确率、方法分布、Top 失败案例。

### Step 5 — 测试

```bash
pytest -q                 # 27 个测试，跑约 5 秒
```

---

## 5. Project Structure

```
calc-multi-solver/
├── README.md                          # 本文件
├── pyproject.toml                     # 依赖固化
├── .env.example                       # DASHSCOPE_API_KEY 模板
├── .gitignore
├── Makefile                           # make install / test / run
│
├── configs/
│   ├── config.yaml                    # K, 并发, 重试, 数据过滤
│   ├── model.yaml                     # 模型 id, 温度
│   └── prompts.yaml                   # 所有 prompt（**严禁硬编码到 .py**）
│
├── data/
│   ├── raw/                           # 原始 parquet（gitignored）
│   └── processed/                     # 转换后的 jsonl + 报告（gitignored）
│
├── logs/                              # 运行日志（gitignored）
│   └── <run_id>/
│       ├── pipeline.jsonl             # 每题一行 EvalResult
│       ├── llm_calls.jsonl            # 所有 LLM 调用（含 token、耗时）
│       ├── traces/<problem_id>.json   # 每题完整 step trace
│       └── summary.md                 # 准确率报告
│
├── src/calc_solver/
│   ├── schema.py                      # Pydantic 数据契约（Problem/Strategy/Solution/EvalResult）
│   ├── data/
│   │   ├── loader.py                  # parquet → Problem (自适应列名映射 + 宽松过滤)
│   │   └── normalizer.py              # 文本/LaTeX 归一化
│   ├── llm/
│   │   ├── client.py                  # QwenClient (异步, 重试, JSON-mode)
│   │   └── prompts.py                 # 从 yaml 加载 prompt
│   ├── tools/
│   │   ├── sympy_tool.py              # diff/integrate/simplify/limit/series/solve/...
│   │   ├── verifier.py                # 五级校验级联 (L1~L5)
│   │   └── latex_parser.py            # latex2sympy2 + sympify 包装
│   ├── agents/
│   │   ├── base.py                    # BaseAgent
│   │   ├── planner.py                 # K 条多样策略
│   │   ├── builder.py                 # ReAct 循环 (think/tool/finish) + 自检
│   │   └── evaluator.py               # 五级校验 + 全错复审 (notes only)
│   ├── orchestrator/
│   │   └── pipeline.py                # 题目级 + 策略级两层并发 + Builder↔Evaluator 循环
│   └── utils/
│       ├── logger.py                  # JSONL 结构化日志
│       └── ids.py                     # run_id 生成
│
├── scripts/
│   ├── inspect_parquet.py             # 数据探查
│   ├── run_batch.py                   # 批量跑题入口
│   └── analyze_results.py             # 结果汇总
│
└── tests/                             # 27 个测试，pytest -q 全通过
    ├── test_loader.py
    ├── test_sympy_tool.py
    ├── test_verifier.py               # L1~L4 各级 + 不定积分 +C + 三角恒等 + 对数合并
    ├── test_planner.py
    ├── test_builder.py
    └── test_evaluator.py
```

---

## 6. Key Configuration (`configs/config.yaml`)

| Section | Setting | Default | 说明 |
|---|---|---|---|
| `run` | `K` | 3 | Planner 产出策略数 |
| `run` | `max_outer_loops` | 2 | **Builder↔Evaluator 重试轮数**（核心循环） |
| `run` | `builder_max_steps` | 12 | 单个 Builder 最多 LLM 轮数 |
| `run` | `builder_max_retries` | 2 | 自检失败后重跑次数 |
| `run` | `problem_concurrency` | 4 | 同时处理几道题 |
| `run` | `builder_concurrency_per_problem` | 3 | 单题内并行 Builder 数 |
| `rate_limits` | `max_concurrent_llm_calls` | 16 | 全局 LLM 并发上限 |
| `data` | `column_overrides` | `{}` | 自动映射失败时手动指定，如 `{question: stem_zh}` |
| `data` | `max_question_chars` | 12000 | 题目长度上限（宽松） |
| `verifier` | `n_samples` | 30 | L4 数值采样点数 |
| `verifier` | `llm_for_unsure` | true | 是否启用 L5 LLM 仲裁 |

---

## 7. Five-Level Verifier (核心)

| 级别 | 方法 | 适用 | confidence |
|---|---|---|---|
| L1 | 字符串归一 | 完全相同 | 1.0 |
| L2 | 符号化简 (`simplify/trigsimp/expand_log/factor/...`) | 表达式 | 0.95 |
| L3 | 类型专用（不定积分比导数；区间/集合直比） | 按 answer_type | 0.95 |
| L4 | 数值采样（30 点，奇点跳过） | 表达式/数值 | 0.9 |
| L5 | LLM 仲裁（仅当 L1-L4 全部不确定且 L4 通过率 ≥50%） | 边界情况 | 0.6 |

**L1-L4 全判错 → 直接 False，不调 LLM**（避免 LLM 把错答洗成对的）。`is_correct` 只能由 Verifier 翻 True，LLM 的「全错复审」只写入 `notes`。

---

## 8. Data Format (本仓库的 parquet)

| 列 | 类型 | 说明 |
|---|---|---|
| `id` | str | 题目唯一 ID（如 `19_15`） |
| `source` | str | 来源编号 |
| `question` | str | 题目原文（含 LaTeX，包裹于 `$...$`） |
| `answer` | str | 标准答案（LaTeX） |
| `solution` | str | 参考解题过程（不参与系统输入） |
| `tag` | dict | 含 `problem_type / have_definite / have_indefinite / is_multi / is_divergent` 等 |
| `reference` | list | 参考资料 |

**Loader 自适应映射**已支持上述列名。如换其他数据集，看 `_schema_report.json` 后在 `configs/config.yaml` 填 `data.column_overrides`。

---

## 9. Three Design Decisions (vs 原始 plan 文档)

1. **Builder ↔ Evaluator 必须循环** — `Pipeline.solve_one` 外层循环 `max_outer_loops=2`，失败时带 `failed_strategies` 提示重新 Plan + Build。
2. **数据过滤宽松** — `loader.py` 只拒空答案/空题/超长/纯图片题，宽松保留 2313/2332 行。
3. **Planner JSON 格式显式** — `configs/prompts.yaml.planner.system` 直接给出 JSON schema 示例，避免 LLM 自由发挥导致解析失败。

---

## 10. Troubleshooting

| 问题 | 解决 |
|---|---|
| `latex2sympy2` 安装失败 | 改用 `pip install latex2sympy2>=1.9.0`（已在 pyproject 固化） |
| `setuptools.backends` 找不到 | 用本仓库的 `pyproject.toml`（已用 `setuptools.build_meta`） |
| 列名识别失败 | 跑 `inspect_parquet.py`，把列名填进 `configs/config.yaml` 的 `data.column_overrides` |
| API 限流 | 调小 `rate_limits.max_concurrent_llm_calls` 与 `run.problem_concurrency` |
| 中断后续跑 | 重跑同一 `--run-id`，`pipeline.jsonl` 已存在的 `problem_id` 自动跳过 |

---


---

## 11. Debugging & Logging (2026-04-29 Updates)

### Log Files (`logs/<run-id>/`)

| File | Contents | New Fields |
|------|----------|-----------|
| `llm_calls.jsonl` | All LLM calls (Planner/Builder/Evaluator) | `content` (raw response), `agent` (planner/builder/evaluator) |
| `pipeline.jsonl` | Per-problem EvalResult summary | unchanged |
| `traces/<id>.json` | Full step-by-step trace per problem | unchanged |
| `llm_verbose.jsonl` | Full request+response (only if `LOG_LLM_VERBOSE=1`) | unchanged |

### Query Logs by Agent

```powershell
# View only Planner responses
Get-Content logs/<run-id>/llm_calls.jsonl | ConvertFrom-Json |
  Where-Object {$_.agent -eq "planner"} | Select-Object content

# View only Builder tool calls
Get-Content logs/<run-id>/llm_calls.jsonl | ConvertFrom-Json |
  Where-Object {$_.agent -eq "builder"} | ForEach-Object {
    $_.content | ConvertFrom-Json | Select-Object action, tool, args
  }

# Count calls per agent
Get-Content logs/<run-id>/llm_calls.jsonl | ConvertFrom-Json |
  Group-Object agent | Select-Object Name, Count
```

### Tool Parameter Format (Builder)

Builder tools now require **exact parameter names** (case-sensitive):

```json
// ? Correct
{"action": "tool", "tool": "differentiate", "args": {"expr_str": "sin(x)", "var": "x"}}

// ? Wrong - parameter name mismatch
{"action": "tool", "tool": "differentiate", "args": {"expression": "sin(x)", "variable": "x"}}
```

**Available tools & exact params**:
| Tool | Required Params |
|------|----------------|
| `parse` | `latex_or_expr`, `var?` |
| `differentiate` | `expr_str`, `var?`, `n?` |
| `integrate_indef` | `expr_str`, `var?` |
| `integrate_def` | `expr_str`, `var`, `a_str`, `b_str` |
| `limit` | `expr_str`, `var`, `point_str`, `direction?` |
| `series` | `expr_str`, `var`, `point_str?`, `n?` |
| `simplify` | `expr_str` |
| `solve` | `expr_str`, `var?` |
| `substitute` | `expr_str`, `mapping_str` |

### Self-Check Logic

For indefinite integrals, Builder now verifies correctness via:
1. Differentiate answer ? compare to integrand
2. **Symbolic simplification**: `simplify(d/dx(answer) - integrand) == 0`?
3. **Numeric sampling**: Evaluate at 6 test points, ?80% match ? pass
4. Fallback: Give benefit of doubt on parse errors

This correctly handles identities like `cos(x) ? 1/sec(x)` that fail string comparison.

### Quick Debug Workflow

```powershell
# 1. Run a minimal test
python scripts/run_batch.py --parquet data/raw/question-v1.parquet --K 1 --max-rows 1 --run-id debug_test

# 2. Check if Planner generated strategies
Get-Content logs/debug_test/llm_calls.jsonl | ConvertFrom-Json |
  Where-Object {$_.agent -eq "planner"} | ForEach-Object { $_.content | ConvertFrom-Json }

# 3. Check Builder tool calls for parameter errors
Get-Content logs/debug_test/llm_calls.jsonl | ConvertFrom-Json |
  Where-Object {$_.agent -eq "builder" -and $_.content -like "*Bad arguments*"}

# 4. Check final result
Get-Content logs/debug_test/pipeline.jsonl | ConvertFrom-Json |
  Select-Object problem_id, is_correct, confidence, chosen_strategy_id
```

## License

MIT
