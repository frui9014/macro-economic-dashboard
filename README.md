# Macro Economic Observatory

一个静态宏观经济 Dashboard 的私有运行仓库。GitHub Actions 每天抓取公开数据、运行质量检查并将最新页面和快照提交回本仓库。

> 仓库保持 Private。当前不启用 GitHub Pages，避免公开再发布 Yahoo Finance 行情数据。

## 页面

- `当日数据`：八维状态、日频温度计、组合观察与学习笔记。
- `时间变化`：指标选择、7 日至 1 年趋势和待接入数据。

## 自动更新

工作流位于 `.github/workflows/daily-update.yml`：

- 每天北京时间 18:30 自动运行。
- 每次运行先安装依赖、执行测试，再按指标发布日历抓取数据。
- 更新 `data/processed/latest.json` 和 `public/` 后，由 GitHub Actions Bot 提交到当前分支。
- 保留手动触发入口，便于立即刷新和故障复查。

## 本地运行

```powershell
python -m unittest discover -s tests -v
python src/update_dashboard.py --output public
```

然后打开 `public/index.html`。

## 查看页面

仓库中的 `public/` 是完整静态页面。为遵守行情数据使用边界，当前不公开部署 Pages；需要在线私密访问时，再选择支持访问控制的托管方案。

## 数据与隐私边界

本仓库只包含公开市场数据、Dashboard 程序和页面资源，不包含个人画像、研究院其他项目或原始研究文档。

页面用于宏观学习与公共政策研究，不构成投资建议。
