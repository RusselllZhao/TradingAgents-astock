# Tushare Pro 第一批缓存与 Token 方案

本文件只设计未来实现边界。本轮不写代码、不保存 token、不调用 API。

## Token 边界

- 不允许把 token 写入源码。
- 不允许把 token 写入文档。
- 不允许把 token 写入 git。
- 未来实现优先读取环境变量：`TUSHARE_TOKEN`。
- 若允许本地配置文件，必须使用 gitignored 文件，例如 `.env.local` 或 `config/local_tushare.toml`。
- 可以提供 example 文件，但只能包含占位符：

```text
TUSHARE_TOKEN=your_tushare_token_here
```

- 错误日志不得打印 token；异常信息进入用户返回前必须脱敏。

## 未来配置建议

| 配置项 | 默认值 | 说明 |
|---|---:|---|
| `TUSHARE_TOKEN` | 无 | 必填 token |
| `TUSHARE_CACHE_DIR` | `.cache/tushare` | 本地缓存目录，必须 gitignore |
| `TUSHARE_MAX_RPM` | 100 | 保守每分钟请求数 |
| `TUSHARE_TIMEOUT_SECONDS` | 15 | 单请求超时 |
| `TUSHARE_ENABLE_CACHE` | true | 是否启用缓存 |

## `.gitignore` 建议

未来代码阶段如新增缓存或本地配置，应忽略：

```gitignore
.env
.env.local
config/local_tushare.toml
.cache/tushare/
docs/recovery/tushare_pro_inventory/runtime_cache/
```

不建议把真实缓存放在 `docs/` 下；若为说明用途，只提交 README/schema，不提交数据。

## 缓存总原则

- 缓存不保存 token。
- 缓存不保存敏感信息。
- 缓存可删除，可重建。
- 缓存键必须包含接口名和关键业务参数。
- 缓存命中时仍应在输出中标注原始 `source=Tushare` 和 `api`，可额外标注 `cache_hit=true`。
- 缓存文件建议 JSON 或 Parquet；第一批优先 JSON，便于调试。

## 接口缓存策略

| 接口 | 缓存键 | TTL / 失效策略 | 备注 |
|---|---|---|---|
| `stock_basic` | `stock_basic/list_status_L.json` | 长缓存；每日或手动刷新 | 全市场静态基础信息，避免重复请求 |
| `daily_basic` | `daily_basic/{ts_code}/{trade_date}.json` | 按交易日缓存；历史交易日长期缓存 | 当前交易日盘后前可短 TTL |
| `balancesheet` | `balancesheet/{ts_code}/{ann_date}_{end_date}.json` | 已公告历史长期缓存；最近报告期每日刷新 | 只取 `ann_date <= as_of` |
| `cashflow` | `cashflow/{ts_code}/{ann_date}_{end_date}.json` | 同上 | 财报修订时可手动刷新 |
| `income` | `income/{ts_code}/{ann_date}_{end_date}.json` | 同上 | 财报修订时可手动刷新 |
| `report_rc` | `report_rc/{ts_code}/{start_date}_{end_date}.json` | 历史窗口长期缓存；近 7 天每日刷新 | 8000 权限后启用主源 |
| `moneyflow` | `moneyflow/{ts_code}/{trade_date}.json` 或 `{start}_{end}.json` | 历史交易日长期缓存；当日盘后前短 TTL | 个股日频资金流 |
| `moneyflow_dc` | `moneyflow_dc/{ts_code}/{trade_date}.json` | 同 moneyflow | 备用源 |

## 频率控制建议

- 所有 Tushare 请求统一通过未来 helper，集中处理频控。
- 默认全局限速：100 rpm。
- `stock_basic` 这类全市场静态接口优先缓存，避免高频调用。
- 财务三表同一股票连续调用时串行，避免三表并发打满频率。
- `report_rc` 即使 8000 权限后，也建议在第一批保持单票按需调用，不做全市场批量抓取。
- 频率限制响应统一转换为短 `technical_error: tushare_rate_limited`。

## 缓存失效策略

- 手动清理：删除缓存目录即可。
- 最近交易日数据：每日刷新。
- 财报最近报告期：公告季内每日刷新；历史报告期长期保存。
- `report_rc` 最近 7 天窗口：每日刷新；更早窗口长期保存。
- 资金流当日数据：盘后前短 TTL，盘后稳定后按日固定。

## 安全与审计

- 返回给 Agent 的文本不得包含 token、请求头、完整 URL 查询中可能含 token 的内容。
- 日志仅记录接口名、ts_code、日期、状态、耗时。
- 缓存元信息可以记录 `created_at`、`source_api`、`params_hash`，不记录 token。

## 第一批不做

- 不提交真实缓存。
- 不设计后台同步任务。
- 不做全市场批量预热。
- 不做 GUI 配置 token。
- 不把 token 放入 notebook、Markdown、CSV、测试输出。

