# Macro Economic Observatory

一个静态宏观经济 Dashboard 的私有备份仓库。

> 云端自动更新和 GitHub Pages 已于 2026-06-19 停用。当前仅在用户明确提出时本地手动更新，不公开再发布 Yahoo Finance 行情数据。

## 页面

- `当日数据`：八维状态、日频温度计、组合观察与学习笔记。
- `时间变化`：指标选择、7 日至 1 年趋势和待接入数据。

## 工作流状态

工作流位于 `.github/workflows/deploy.yml`，当前在 GitHub 中处于手动禁用状态，并且代码只保留手动触发入口。若未来更换为允许再发布的数据源，需要重新完成许可审计后才能恢复。

## 本地运行

```powershell
python -m unittest discover -s tests -v
python src/update_dashboard.py --output public
```

然后打开 `public/index.html`。

## GitHub Pages 设置

1. 创建独立仓库并仅上传本目录内容。
2. 在仓库 `Settings → Pages` 中将部署来源设为 `GitHub Actions`。
3. 在 `Actions` 中首次手动运行 `Update and deploy macro dashboard`。
4. 部署完成后，从 Pages 设置或 Actions 部署记录打开站点地址。

## 数据与隐私边界

本仓库只包含公开市场数据、Dashboard 程序和页面资源，不包含个人画像、研究院其他项目或原始研究文档。

页面用于宏观学习与公共政策研究，不构成投资建议。
