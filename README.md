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

程序不会把 API Key、Token、Cookie 或账号密码写入代码和 JSON。GPT 解读默认关闭；没有密钥时完整展示规则分析。若需启用，只在 Repository Secret `OPENAI_API_KEY` 中配置密钥，可在 Repository Variable `OPENAI_MODEL` 中指定模型。GPT 只解释规则输入包，不得修改分数、标签或置信度；调用失败不会中断页面更新。

分析层将缺失指标记为 `null`，不以0代替；使用考虑正常发布滞后的新鲜度闸门（日频5天、周频21天、月度75天、季度160天、年度550天，个别来源可覆盖），陈旧数据仅作背景。

一句话判断、宏观状态、背离和可选 GPT 均受证据硬闸门约束。只有置信度至少为“中”、绝对分数达到0.5且至少有2项核心指标有效的维度，才能进入主判断；低置信度信号仅作为风险提示。季节性流量优先比较上年同期和近3期趋势，不使用简单月环比。

每项指标区分数据所属期、官方发布时间、系统抓取时间及本次是否变值；仅今天发布或本次数值变化的指标计入“今日新增”。

页面用于宏观学习与公共政策研究，不构成投资建议。
