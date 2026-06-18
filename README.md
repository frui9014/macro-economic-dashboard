# Macro Economic Observatory

一个自动更新的静态宏观经济 Dashboard。每天北京时间 18:30，由 GitHub Actions 抓取公开数据、运行计算测试并发布到 GitHub Pages。

## 页面

- `当日数据`：八维状态、日频温度计、组合观察与学习笔记。
- `时间变化`：指标选择、7 日至 1 年趋势和待接入数据。

## 自动更新

工作流位于 `.github/workflows/deploy.yml`：

- 每天 10:30 UTC 运行，对应北京时间 18:30。
- 支持在 GitHub Actions 页面手动运行。
- 推送到 `main` 时也会运行，用于首次发布和代码更新。
- 数据源失败时保留上次有效值并显式标记，不伪造数据。

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
