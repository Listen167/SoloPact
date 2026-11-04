# 安装与运行说明

## 环境依赖

- Docker Desktop 4.x及以上
- Docker Compose v2
- 推荐内存4GB以上

## 一键启动

在作品根目录执行：

```powershell
Copy-Item .env.example .env
docker compose up --build
```

浏览器访问 <http://localhost:8080>。首次启动会自动创建数据库并载入完全合成的演示数据。

如果8080端口已被占用，在 `.env` 中设置 `FRONTEND_PORT=8081` 后重新启动。

## 演示恢复

点击页面右上角“重置演示”，或调用：

```powershell
Invoke-WebRequest -Method Post http://localhost:8080/api/demo/reset
```

## 停止

```powershell
docker compose down
```

数据库和上传文件保存在Docker具名卷中。需要清空数据时才执行 `docker compose down -v`，该命令会永久删除本项目的本地演示卷。

## 开源组件

FastAPI、SQLAlchemy、Pydantic、PyMuPDF、React、Ant Design、ECharts、PostgreSQL、Nginx。具体版本见后端requirements与前端package-lock。

## 码道应用总结

提交前依据 `codearts_proof/evidence-index.csv` 填写真实使用总结，并附完整截图，不得使用示例占位内容冒充证据。

