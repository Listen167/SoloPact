# SoloPact

**Business commitments, under control.**

SoloPact 是面向独立顾问、自由职业者与小型专业服务工作室的经营承诺与现金流 Agent。当前 MVP 聚焦合同到回款：将合同付款条款转为可核对的应收计划，导入银行流水后执行确定性匹配，标记逾期、临期和金额不符风险，并生成带合同证据的催款草稿。后续将沿着经营收件箱、履约承诺和行动中心扩展，而不是发展成传统 ERP。

> 产品只提供经营信息整理与沟通辅助，不提供会计、税务、法律或投资建议，也不会自动向客户发送消息。

## 已实现

- PDF/TXT合同上传、数字PDF提取和可选华为云OCR扫描件识别
- 合同与付款节点结构化抽取，保留页码、原文和置信度
- 人工核对后进入应收台账，所有确认操作写入审计日志
- CSV/XLSX银行流水导入，中英文常见列名自动映射和重复检测
- 金额、客户、日期、合同编号四维确定性匹配
- 自动匹配、人工复核与未关联流水严格分离，重复运行不会复用已核销流水
- 逾期、14天内到期与疑似金额不符风险
- 邮件/微信催款草稿、复制、导出和人工审核状态
- 可重复重置的合成演示租户与外部服务降级方案

## 一键运行

需要 Docker Desktop：

```powershell
Copy-Item .env.example .env
docker compose up --build
```

访问 <http://localhost:8080>，API文档位于 <http://localhost:8080/api/docs>。开发模式API文档为 <http://localhost:8000/api/docs>。

若8080端口已占用，可在 `.env` 中设置 `FRONTEND_PORT=8081` 后访问对应端口。

## 本地开发

后端：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --reload --port 8000
```

前端另开终端：

```powershell
Set-Location frontend
npm install
npm run dev
```

访问 <http://localhost:5173>。开发服务器会把 `/api` 代理到后端。

## 质量检查

```powershell
.\.venv\Scripts\python.exe -m pytest --cov=backend.app
.\.venv\Scripts\ruff.exe check backend
Set-Location frontend
npm run lint
npm run build
```

## 华为云接入

默认无需云账号即可运行。配置 `.env` 后可启用：

- OBS：设置 `HUAWEI_OBS_ENDPOINT`、访问密钥和存储桶。
- OCR：设置 `HUAWEI_OCR_ENDPOINT`、`HUAWEI_OCR_TOKEN`、`HUAWEI_OCR_PROJECT_ID`。
- 模型服务：设置兼容 Chat Completions 的 `MODEL_BASE_URL`、`MODEL_API_KEY`、`MODEL_NAME`。

未配置或调用失败时，系统分别降级到本地文件存储、数字PDF文本提取和确定性催款模板。生产部署应改用短期IAM凭证或云端委托，不应把长期密钥写入镜像。

## 比赛交付

- `docs/`：提案、架构、API与演示说明
- `ppt/`：答辩材料提纲
- `video/`：三分钟视频分镜
- `codearts_proof/`：码道真实使用证据的整理规范与索引
- `readme/`：提交包安装说明

后续功能的优先级、依赖关系与验收标准见 [`docs/implementation-roadmap.md`](docs/implementation-roadmap.md)。

执行 `scripts/package.ps1` 会在 `output/` 下生成符合官方五目录规范的ZIP。脚本不会伪造PPT、视频、用户访谈或码道截图；这些材料必须在提交前由参赛者补齐。

