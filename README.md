# MaxOracle - Lotto Max 历史分析与推荐

> 免责声明：彩票结果具有随机性，任何推荐不保证中奖。本网站仅用于统计学习与可视化展示，不构成博彩建议。

## 项目简介

MaxOracle 使用 Python + Django 构建，聚焦 OLG Lotto Max 历史中奖号码分析与可视化，并生成 5 条下一期推荐号码。系统具备可配置数据源、可扩展分析与推荐策略、管理后台与部署方案。

## 功能清单

- 历史开奖抓取（至少 1000 期，支持增量更新）
- 统计分析：频次、概率、遗漏、冷热、组合、分布
- 图表可视化（Chart.js，至少 4 张图表）
- 推荐引擎：热冷平衡 + 结构约束 + 组合信号 + 多样性控制 + 可复现种子
- 管理后台：数据查看、过滤、手动触发 re-ingest
- Docker + docker-compose 部署

## 规则说明（OLG）

- 主抽奖：从 1–50 中开出 7 个主号 + 1 个 Bonus 号，共 8 个号码且互不重复。
- 中奖类别至少包含：7/7、6/7+Bonus、6/7、5/7+Bonus、4/7、3/7+Bonus 等。“+” 表示命中 Bonus 号。
- $5 play 通常包含 3 组（3 selections）号码，本项目以“每组 7 个号码”为分析单位。
- MaxMillions：当 jackpot 达到门槛出现的额外抽奖，规则与主抽奖不同。当前版本先聚焦主抽奖与 Bonus。
- 数据源配置化，便于未来切换至其他省份规则页面。

## 目录结构

```
maxoracle/
apps/lotto/
  models.py
  services/
    analytics.py
    recommender.py
    scrapers/
  management/commands/
  templates/lotto/
  static/lotto/
```

## 本地启动

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py ingest_lottomax --since 2010-01-01
python manage.py runserver
```

访问：
- 主页：http://127.0.0.1:8000/
- 分析页：http://127.0.0.1:8000/analysis/
- 推荐页：http://127.0.0.1:8000/recommendations/
- 管理后台：http://127.0.0.1:8000/admin/

## 导入数据（命令行）

```bash
python manage.py ingest_lottomax --since 2010-01-01 --source auto
```

参数：
- `--since YYYY-MM-DD`：仅导入指定日期之后的开奖
- `--max-pages N`：最大页数（如数据源支持分页）
- `--source`：指定数据源（`olg`/`lotto8`/`auto`）
- `--incremental`：自动从数据库最新一期日期开始增量更新（与 `--since` 二选一）

### 增量更新（推荐）

首次全量导入完成后，之后可以在每周二/五开奖后跑增量更新：

```bash
python manage.py ingest_lottomax --incremental --source lotto8
```

### 定时任务（cron / Launchd）

**cron（Linux/macOS）**：

```bash
crontab -e
```

示例（每周二、五 23:30 运行）：

```bash
30 23 * * 2,5 /bin/bash -lc 'source /opt/anaconda3/etc/profile.d/conda.sh && conda activate maxoracle && cd /Users/yinwang/Programming/MaxOraclePython && python manage.py ingest_lottomax --incremental --source lotto8 >> /tmp/maxoracle_ingest.log 2>&1'
```

**Launchd（macOS）**：

保存为 `~/Library/LaunchAgents/com.maxoracle.ingest.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key><string>com.maxoracle.ingest</string>
    <key>ProgramArguments</key>
    <array>
      <string>/bin/bash</string>
      <string>-lc</string>
      <string>source /opt/anaconda3/etc/profile.d/conda.sh && conda activate maxoracle && cd /Users/yinwang/Programming/MaxOraclePython && python manage.py ingest_lottomax --incremental --source lotto8</string>
    </array>
    <key>StartCalendarInterval</key>
    <array>
      <dict><key>Weekday</key><integer>2</integer><key>Hour</key><integer>23</integer><key>Minute</key><integer>30</integer></dict>
      <dict><key>Weekday</key><integer>5</integer><key>Hour</key><integer>23</integer><key>Minute</key><integer>30</integer></dict>
    </array>
    <key>StandardOutPath</key><string>/tmp/maxoracle_ingest.log</string>
    <key>StandardErrorPath</key><string>/tmp/maxoracle_ingest.err</string>
  </dict>
</plist>
```

加载并启动：

```bash
launchctl load -w ~/Library/LaunchAgents/com.maxoracle.ingest.plist
```

### LotteryPost 数据源（可选）

如果需要使用 LotteryPost（Cloudflare 保护），请先安装浏览器依赖：

```bash
pip install playwright
playwright install chromium
```

然后运行：

```bash
python manage.py ingest_lottomax --since 2010-01-01 --source lotterypost
```

### 导入日志示例（示意）

```
INFO lotto Starting ingestion: source=auto since=2010-01-01 max_pages=None
INFO lotto Fetching olg from https://www.olg.ca/en/lotto-max/past-results.html
INFO lotto Fetching lotto8 from https://www.lotto-8.com/canada/listltoCAMAX.asp
INFO lotto Ingestion completed: Processed 1104 draws, added 1097, skipped 7
```

> 实际日志以你的运行结果为准。建议导入后在“数据”页确认期数与最近一期信息。

## 测试

```bash
python manage.py test apps.lotto
```

## 部署（Docker）

```bash
docker-compose up --build
```

服务：
- Web: http://localhost:8000
- Postgres: localhost:5432

## 配置

环境变量（参考 `.env.example`）：
- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `DJANGO_ALLOWED_HOSTS`
- `LOTTO_WINDOW`
- `LOTTO_ROLLING_WINDOW`
- `LOTTO_RECOMMENDATION_COUNT`
- `LOTTO_RECOMMENDATION_SEED`

数据源可在 `maxoracle/settings.py` 的 `LOTTO_CONFIG` 中配置与扩展。

## 部署（Railway）

1) 在 Railway 创建项目并连接 GitHub 仓库 `yin-se/MaxOracle`  
2) 添加 PostgreSQL 插件（Railway 会提供 `DATABASE_URL`）  
3) 设置环境变量：
   - `DJANGO_SECRET_KEY`（必填）
   - `DJANGO_DEBUG=0`
   - `DJANGO_ALLOWED_HOSTS=<你的 Railway 域名，例如 maxoracle.up.railway.app>`
4) 在部署后运行一次数据库迁移（Railway 的 “Run command” 或 CLI）：

```bash
python manage.py migrate
```

5) （可选）首次导入数据：

```bash
python manage.py ingest_lottomax --since 2009-09-25 --source lotto8
```

6) Railway 默认会使用 `Procfile` 启动：  
`gunicorn maxoracle.wsgi:application --bind 0.0.0.0:$PORT`

## 可扩展点

- 添加更多数据源（实现新的 scraper 并注册）
- 引入 Redis 缓存或异步任务队列
- 扩展 MaxMillions 统计与展示
