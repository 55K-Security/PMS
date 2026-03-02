# PMS 项目管理系统

基于 Django + Bootstrap 的企业级项目管理系统，提供项目任务管理，甘特图、周计划，系统监控等功能。

## 项目简介

PMS (Project Management System) 是一套完整的项目管理解决方案，支持多项目管理、任务分配、进度跟踪，甘特图可视化、周计划管理，系统监控等功能。

## 技术栈

- **后端**: Python 3.x + Django 4.x
- **前端**: HTML5 + CSS3 + JavaScript + Bootstrap 5
- **数据库**: SQLite (默认) / MySQL / PostgreSQL
- **图表**: Chart.js
- **系统监控**: psutil

## 支持的操作系统

- **Windows**: Windows 10/11 (推荐)
- **Linux**: Ubuntu 20.04+, CentOS 8+, Debian 11+
- **macOS**: macOS 11 (Big Sur) 及更高版本

> 注意：项目已在 Windows 11 环境下开发测试，Linux/macOS 理论上完全兼容

## 功能模块

### 1. 项目管理
- 项目列表、创建、编辑、删除
- 项目状态管理（未开始、进行中、已完成、逾期未完结）
- 项目甘特图可视化
- 项目进度跟踪

### 2. 任务管理
- 任务列表、创建、编辑、删除
- 任务状态管理
- 任务负责人分配
- 四象限任务视图（重要紧急、重要不紧急、紧急不重要、不紧急不重要）

### 3. 甘特图
- 项目视图 / 任务视图 切换
- 按天展示时间线
- 动态日期范围

### 4. 周计划
- 工作日创建限制（仅周一至周五）
- 休息日自动标记
- 现代化卡片设计

### 5. 预算成本
- 预算项目管理
- 费用记录与统计

### 6. 系统监控
- CPU 使用率实时监控
- 内存使用率监控
- 磁盘使用率监控
- 网络速率监控
- 趋势图表展示
- 实时/定时模式切换
- 时间范围选择

### 7. 看板
- 项目统计概览
- 任务完成率展示
- 数据源配置

### 8. 日志管理
- 操作日志记录
- 系统日志记录
- 日志筛选与导出（CSV/Excel）

### 9. 系统设置
- AI 配置
- 邮件配置
- 安全设置（验证码）
- 界面定制（Logo、登录背景）
- 版本升级

### 10. 帮助文档
- 功能说明
- 操作指南
- 分类查阅

## 项目结构
```bash
pms/
├── pms/                      # Django 项目配置
│   ├── settings.py          # 项目设置
│   ├── urls.py              # 主路由配置
│   └── wsgi.py             # WSGI 配置
├── pmsapp/                  # 主应用
│   ├── models.py           # 数据模型
│   ├── views.py            # 视图函数
│   ├── urls.py             # 应用路由
│   ├── admin.py            # 管理后台配置
│   ├── middleware.py       # 中间件
│   ├── migrations/         # 数据库迁移
│   └── tests/              # 测试文件
├── templates/                # 模板目录
│   ├── base.html           # 基础模板
│   ├── login.html          # 登录页
│   ├── index.html          # 首页
│   ├── project/            # 项目相关模板
│   ├── task/               # 任务相关模板
│   ├── weekly/             # 周计划模板
│   ├── budget/             # 预算模板
│   ├── monitor/            # 监控模板
│   ├── settings/           # 设置模板
│   ├── help/               # 帮助文档模板
│   └── ...
├── static/                  # 静态文件
│   └── css/
│       └── style.css       # 样式文件
├── media/                   # 上传文件目录
│   └── version_upgrades/  # 升级包存储
├── docs/                    # 文档目录
├── manage.py                # Django 管理脚本
├── db.sqlite3             # SQLite 数据库
└── README.md               # 说明文档
```

## 部署环境要求

### 基础环境
```bash
- Python 3.8 或更高版本
- pip 包管理器
```
### Python 依赖
```bash
Django>=4.0
Pillow>=9.0
openpyxl>=3.0
psutil>=5.9
```

## 安装步骤（跨平台通用）

以下步骤已考虑 Windows/Linux/macOS 的差异，请根据您的操作系统选择对应命令。

### 1. 前置检查
检查 Python 版本（需要 ≥3.8）：
```bash
# Linux/macOS
python3 --version

# Windows (在命令提示符或 PowerShell 中)
python --version   # 或 python3 --version
```
如果未安装 Python，请参考：
- **Ubuntu/Debian**: `sudo apt update && sudo apt install python3 python3-venv python3-pip -y`
- **CentOS/RHEL**: `sudo yum install python3 python3-venv python3-pip -y`
- **macOS**: `brew install python3`（需安装 Homebrew）
- **Windows**: 从 [python.org](https://www.python.org/downloads/) 下载安装包，安装时务必勾选“Add Python to PATH”。

### 2. 克隆项目
```bash
git clone https://github.com/xxx/pms.git   # 替换为实际仓库地址
cd pms
```
> Windows 下若未安装 Git，可先安装 [Git for Windows](https://git-scm.com/download/win) 或直接下载项目 ZIP 包解压。

### 3. 创建并激活虚拟环境（强烈推荐）
虚拟环境可以隔离项目依赖，避免与系统其他 Python 包冲突。

**创建虚拟环境**（所有系统通用）：
```bash
python -m venv venv    # Windows 使用 python，Linux/macOS 可使用 python3
```
这将在当前目录生成一个 `venv` 文件夹。

**激活虚拟环境**（按操作系统选择）：
- **Linux/macOS** (bash/zsh):
  ```bash
  source venv/bin/activate
  ```
- **Windows** (命令提示符 cmd):
  ```cmd
  venv\Scripts\activate.bat
  ```
- **Windows** (PowerShell):
  ```powershell
  Set-ExecutionPolicy RemoteSigned -Scope CurrentUser -Force   # 仅首次需要，允许执行脚本
  venv\Scripts\Activate.ps1
  ```

激活成功后，命令行提示符前会出现 `(venv)` 标识。

### 4. 升级 pip 并安装依赖
首先升级 pip 到最新版本：
```bash
pip install --upgrade pip
```
然后安装项目依赖。**推荐使用项目提供的 `requirements.txt`**（若存在）：
```bash
pip install -r requirements.txt
```
如果没有 `requirements.txt`，可以手动安装核心依赖（指定兼容版本）：
```bash
pip install Django==4.2.10 Pillow==10.2.0 openpyxl==3.1.2 psutil==5.9.8
```

### 5. 数据库初始化
执行数据库迁移，创建数据表：
```bash
# 如果项目已包含迁移文件（即 pmsapp/migrations/ 目录下有文件），则直接迁移即可
python manage.py migrate

# 若项目未包含迁移文件（首次克隆），需要先生成迁移文件再迁移
python manage.py makemigrations
python manage.py migrate
```
> **说明**：`makemigrations` 用于将模型变更生成迁移脚本，如果项目已提交迁移文件（通常应提交），可以跳过该步骤，直接 `migrate`。

创建超级管理员账户（用于登录后台）：
```bash
python manage.py createsuperuser
```
按提示输入用户名、邮箱、密码（密码需 8 位以上，且有一定复杂度）。

### 6. 启动开发服务器
- **仅本地访问**（默认 127.0.0.1:8000）：
  ```bash
  python manage.py runserver 8000
  ```
- **局域网/公网访问**（需修改 `settings.py` 中的 `ALLOWED_HOSTS` 添加相应 IP 或域名）：
  ```bash
  python manage.py runserver 0.0.0.0:8000
  ```
如果 8000 端口被占用，可更换其他端口，例如 `python manage.py runserver 8001`。

启动后，访问 `http://127.0.0.1:8000` 即可进入系统。

### 7. 退出虚拟环境（可选）
当不再需要时，可退出虚拟环境：
```bash
deactivate
```

### 默认账户
- **用户名**: admin
- **密码**: Admin@2024

> 首次登录后建议立即修改密码。

## 主要功能入口

| 功能 | 路径 |
|------|------|
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

## 系统预览

### 登录页面
- 现代化UI设计
- 验证码验证
- 主题适配

### 首页
- 项目统计
- 任务概览
- 快捷入口

### 甘特图
- 日时间线展示
- 项目/任务视图切换

### 系统监控
- CPU/内存/磁盘/网络四维监控
- 实时趋势图表
- 时间范围选择

## 开发说明

### 添加新的功能模块
1. 在 `pmsapp/models.py` 中定义数据模型
2. 在 `pmsapp/views.py` 中添加视图函数
3. 在 `pmsapp/urls.py` 中配置路由
4. 在 `templates/` 中创建对应模板

### 运行测试
```bash
python manage.py test pmsapp.tests
```

### 生成迁移
```bash
python manage.py makemigrations
python manage.py migrate
```

## 注意事项

1. **安全**: 生产环境请修改 `SECRET_KEY`，并将 `DEBUG` 设置为 `False`；同时正确配置 `ALLOWED_HOSTS`。
2. **数据库**: 生产环境建议使用 MySQL 或 PostgreSQL，并配置对应数据库驱动。
3. **上传文件**: 确保 `media/` 目录可写，用于存储上传的升级包等。
4. **日志**: 建议配置日志轮转，避免日志文件过大。
5. **暴露服务**: 使用 `0.0.0.0` 监听时，务必确保 Django 的 `ALLOWED_HOSTS` 已包含实际访问的域名/IP，且最好通过 Nginx/Apache 等反向代理，不要直接暴露开发服务器到公网。

## 部署脚本分析与优化建议

以下是针对部署脚本的详细分析与优化建议，供开发者参考，以确保部署过程更加稳健、跨平台兼容。

---

### 正确性评估
原始脚本基本正确，覆盖了多平台，但存在以下可优化点：
- **命令统一性**：激活虚拟环境后，建议统一使用 `python` 命令（而不是 `python3`），因为虚拟环境中的 `python` 已指向正确解释器。
- **PowerShell 执行策略**：激活脚本需要执行策略调整，注释中已包含，但可补充说明。
- **依赖安装**：强调优先使用 `requirements.txt`，避免遗漏依赖。
- **makemigrations 适用性**：如果项目已自带迁移文件，无需执行 `makemigrations`，直接 `migrate` 即可。
- **安全提示**：公网访问时需配置 `ALLOWED_HOSTS` 并考虑反向代理。

### 优化后的跨平台安装步骤
（已体现在前文的“安装步骤”中，此处不再重复）

### 总结
通过上述优化，部署脚本更加清晰、健壮，适用于不同操作系统的开发者。建议在项目文档中采用统一的 `python` 命令，并附带必要的安全提醒。

---

## 更新日志

### v1.0.0
- 初始版本发布
- 完整的项目管理功能
- 系统监控模块
- 甘特图可视化
- 周计划管理
- 日志审计
- 帮助文档

## 许可证

MIT License

## 联系方式

如有问题，请提交 Issue 或联系维护者。