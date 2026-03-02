# PMS 项目管理系统 v1.0.0 发行说明

**版本**: v1.0.0  
**发布日期**: 2026-03-02  
**状态**: 正式发布

---

## 版本简介

PMS (Project Management System) 是一套基于 Django + Bootstrap 开发的企业级项目管理系统的首个正式版本。该系统提供完整的项目管理、任务管理、甘特图、周计划、系统监控等功能，适用于中小型团队的日常项目管理需求。

---

## 技术栈

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | 3.8+ | 后端 runtime |
| Django | 4.x | Web 框架 |
| Bootstrap | 5.x | 前端 UI 框架 |
| Chart.js | - | 图表可视化 |
| psutil | 5.9+ | 系统监控 |
| Pillow | 9.0+ | 图像处理（验证码） |
| openpyxl | 3.0+ | Excel 导出 |

---

## 系统要求

### 支持的操作系统
- Windows 10/11 (推荐)
- Linux (Ubuntu 20.04+, CentOS 8+, Debian 11+)
- macOS 11+

### 运行环境
- Python 3.8 或更高版本
- pip 包管理器

---

## 默认账户

| 类型 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | admin | Admin@2024 |

> 首次登录后请及时修改密码

---

## 目录结构

```
pms/
├── pms/                   # Django 项目配置
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── pmsapp/               # 主应用
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── admin.py
│   └── middleware.py
├── templates/            # HTML 模板
│   ├── base.html
│   ├── login.html
│   ├── index.html
│   └── ...
├── static/              # 静态文件
│   └── css/
│       └── style.css
├── media/              # 上传文件
├── manage.py           # Django 管理脚本
└── README.md          # 项目说明
```

---

## 主要功能入口

| 功能 | URL |
|------|-----|
| 登录页 | /login/ |
| 首页 | / |
| 项目列表 | /list/ |
| 甘特图 | /gantt/ |
| 任务列表 | /task/list/ |
| 周计划 | /weekly/plan_list/ |
| 预算成本 | /budget/list/ |
| 四象限 | /quadrant/list/ |
| 团队管理 | /user/list/ |
| 文件管理 | /files/ |
| 系统监控 | /monitor/ |
| 看板 | /dashboard-big/ |
| 日志 | /settings/logs_upgrade/ |
| 设置 | /settings/ |
| 帮助文档 | /help/ |

---

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| v1.0.0 | 2026-03-02 | 首个正式版本 |

---

## 已知问题

- 暂无

---

## 更新计划

- [ ] 用户权限管理模块
- [ ] 报表导出功能
- [ ] 移动端适配优化
- [ ] API 接口开放

---

## 许可证

MIT License

---

## 联系方式

- 问题反馈: https://github.com/your-repo/pms/issues
- 技术支持: support@example.com

---

**感谢您使用 PMS 项目管理系统！**
