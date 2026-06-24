# Macro Economic Observatory

一个公开访问的静态宏观经济 Dashboard。GitHub Actions 每天抓取公开宏观经济数据、运行质量检查、更新快照并部署 GitHub Pages。

> 本项目仅包含公开宏观经济与公开市场数据，不包含个人画像、私人研究材料、API Key、Token、Cookie、账号密码或其他私人信息。

## 页面

- `当日数据`：八维状态、日频温度计、组合观察与学习笔记。
- `时间变化`：按全部、每日、月度、季度和年度筛选指标；横轴、起止时间及快捷周期随更新频率联动。
- `分析判断`：规则化8维打分、7组关系诊断、背离、候选宏观状态和可选 GPT 解读。

## 自动更新

工作流位于 `.github/workflows/daily-update.yml`：

- 每天北京时间 18:30 自动运行。
- 每次运行先安装依赖、执行测试，再按指标发布日历抓取数据。
- 更新 `data/daily_snapshot.json`、`data/processed/latest.json`、`data/analysis/`、每日 Markdown 报告和 `public/` 后，由 GitHub Actions Bot 提交到当前分支。
- 保留手动触发入口，便于立即刷新和故障复查。
- 每次成功更新后，将 `public/` 部署到公开 GitHub Pages。

## 本地运行

```powershell
python -m unittest discover -s tests -v
python src/update_dashboard.py --output public
python src/run_analysis.py
```

然后打开 `public/index.html`。

## 公开网页

- GitHub Pages：`https://frui9014.github.io/macro-economic-dashboard/`
- 仓库中的 `public/` 是同一页面的完整静态文件。

## 数据与隐私边界

本仓库只包含公开宏观经济与公开市场数据、Dashboard 程序和页面资源，不包含个人画像、研究院其他项目、私人信息或原始研究文档。

程序不会把 API Key、Token、Cookie 或账号密码写入代码、JSON、前端页面或仓库。GPT 解读默认关闭；没有密钥时完整展示规则分析，并提示“未启用 GPT 解读，仅展示规则引擎分析结果”。GPT 只解释单独生成的最小化规则输入包，不得修改分数、标签或置信度；调用失败不会中断页面更新。Dashboard 内部 `analysis` 仍保留完整规则分析结构；`data/analysis/daily_macro_payload.json` 仅保留 `date`、`dimension_scores`、`relation_diagnostics`、`detected_divergences`、`candidate_macro_states`、`important_data_updates` 和 `missing_or_stale_data`，不包含完整指标分数、历史序列或原始值摘要。

## 启用 GPT 解读

云端启用方式：

1. 打开 GitHub 仓库 `Settings → Secrets and variables → Actions`。
2. 进入 `Secrets`，新增 `OPENAI_API_KEY`，值填写你的 OpenAI API Key。
3. 可选：继续在 `Secrets` 中新增 `OPENAI_MODEL`，例如 `gpt-4.1-mini`；如果不设置，程序默认使用 `gpt-4.1-mini`。
4. 保存后，手动运行一次 GitHub Actions，或等待每天北京时间 18:30 自动运行。

本地启用方式：

```powershell
$env:OPENAI_API_KEY="你的 OpenAI API Key"
$env:OPENAI_MODEL="gpt-4.1-mini"
python src/run_analysis.py
```

如果不设置 `OPENAI_API_KEY`，程序不会报错，会生成 fallback `data/analysis/macro_judgement.json`，页面继续展示规则引擎分析。确认结果时，打开 `data/analysis/macro_judgement.json`：

- `gpt_enabled: true` 且 `gpt_status: "ok"`：GPT 解读已生成。
- `gpt_enabled: false` 且 `gpt_status: "not_configured"`：未配置 API Key，使用 fallback。
- `gpt_enabled: false` 且 `gpt_status: "api_failed"`：已配置但调用失败，使用 fallback。

安全检查：

- `.gitignore` 已包含 `.env` 和 `.env.*`。
- 不提交 `.env`。
- 不在 `src/web/app.js`、`index.html` 或任何前端文件中调用 OpenAI API。
- GPT 调用只允许发生在 GitHub Actions 或本地 Python 脚本中。

分析层将缺失指标记为 `null`，不以0代替；使用考虑正常发布滞后的新鲜度闸门（日频5天、周频21天、月度75天、季度160天、年度550天，个别来源可覆盖），陈旧数据仅作背景。

一句话判断、宏观状态、背离和可选 GPT 均受证据硬闸门约束。只有置信度至少为“中”、绝对分数达到0.5且至少有2项核心指标有效的维度，才能进入主判断；低置信度信号仅作为风险提示。季节性流量优先比较上年同期和近3期趋势，不使用简单月环比。

每项指标区分数据所属期、官方发布时间、系统抓取时间及本次是否变值；仅今天发布或本次数值变化的指标计入“今日新增”。

页面用于宏观学习与公共政策研究，不构成投资建议。
