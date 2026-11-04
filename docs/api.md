# API 摘要

交互文档由FastAPI在 `/api/docs` 自动生成。所有业务请求默认使用演示租户，也可传入 `X-Tenant-ID`。

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/health` | 数据库与Provider状态 |
| POST | `/api/demo/reset` | 恢复合成演示数据 |
| POST | `/api/documents` | 上传合同、发票或其他文档 |
| GET | `/api/contracts` | 合同与付款节点台账 |
| PATCH | `/api/contracts/{id}/review` | 人工修正并确认抽取结果 |
| POST | `/api/bank-imports` | 导入CSV/XLSX银行流水 |
| POST | `/api/reconciliation-runs` | 执行幂等匹配 |
| GET | `/api/reconciliation-matches` | 查询匹配及评分依据 |
| GET | `/api/dashboard` | 驾驶舱指标、节点与风险 |
| GET | `/api/alerts` | 开放风险队列 |
| POST | `/api/alerts/{id}/draft` | 生成催款草稿 |
| PATCH | `/api/drafts/{id}` | 标记草稿已人工审核 |
| GET | `/api/audit-events` | 查询审计事件 |

