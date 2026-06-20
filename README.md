# Macro Economic Observatory

一个公开访问的静态宏观经济 Dashboard。GitHub Actions 每天抓取公开宏观经济数据、运行质量检查、更新快照并部署 GitHub Pages。

> 本项目仅包含公开宏观经济与公开市场数据，不包含个人画像、私人研究材料、API Key、Token、Cookie、账号密码或其他私人信息。

## 页面

- `当日数据`：八维状态、日频温度计、组合观察与学习笔记。
- `时间变化`：按全部、每日、月度、季度和年度筛选指标；横轴、起止时间及快捷周期随更新频率联动。

## 自动更新

工作流位于 `.github/workflows/daily-update.yml`：

- 每天北京时间 18:30 自动运行。
- 每次运行先安装依赖、执行测试，再按指标发布日历抓取数据。
- 更新 `data/daily_snapshot.json`、`data/processed/latest.json` 和 `public/` 后，由 GitHub Actions Bot 提交到当前分支。
- 保留手动触发入口，便于立即刷新和故障复查。
- 每次成功更新后，将 `public/` 部署到公开 GitHub Pages。

## 本地运行

```powershell
python -m unittest discover -s tests -v
python src/update_dashboard.py --output public
```

然后打开 `public/index.html`。

## 公开网页

- GitHub Pages：`https://frui9014.github.io/macro-economic-dashboard/`
- 仓库中的 `public/` 是同一页面的完整静态文件。

## 数据与隐私边界

本仓库只包含公开宏观经济与公开市场数据、Dashboard 程序和页面资源，不包含个人画像、研究院其他项目、私人信息或原始研究文档。

程序不会把 API Key、Token、Cookie 或账号密码写入代码和 JSON。未来若数据源需要密钥，只通过 GitHub Repository Secrets 注入。

页面用于宏观学习与公共政策研究，不构成投资建议。
