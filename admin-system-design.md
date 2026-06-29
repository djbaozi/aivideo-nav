# djbaozi 导航站 — 后台管理系统设计方案

> 项目路径: `/Users/mac/Desktop/aivideo-nav/`
> 当前状态: 纯静态HTML，手动修改数据

---

## 一、技术选型建议

### 推荐方案：Flask + SQLite （适合单机/小团队，可落地）

| 对比维度 | **Flask + SQLite** ✅ | Node.js + SQLite | Serverless + JSON |
|----------|----------------------|------------------|-------------------|
| 学习成本 | 低（Python人人会） | 中 | 中高 |
| 部署复杂度 | 1条命令启动 | 需装Node | 需云函数 |
| 数据一致性 | 强（SQL事务） | 强 | 弱（JSON并发） |
| 开发速度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| 扩展性 | 够用（可升MySQL） | 够用 | 好 |
| SEO/SSR | 可Jinja2模板 | 需额外 | 无 |

**最终推荐：Flask + SQLite + Jinja2模板 + Bootstrap 5**

理由：
- Python是项目已有语言（已有 gen-article.py）
- SQLite单文件数据库，无需装MySQL
- Jinja2模板直接生成HTML，保留SEO
- 无需前端框架，后台页面用Bootstrap 5即可
- 一天可出MVP

---

## 二、数据模型设计

### 2.1 工具表（tools）

```sql
CREATE TABLE tools (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,          -- 工具名称
    icon        TEXT,                   -- 图标（emoji/URL/文件名）
    description TEXT,                   -- 简短描述
    url         TEXT NOT NULL,          -- 工具链接
    category    TEXT NOT NULL,          -- 分类（文本分类/图像生成/视频生成/音频...）
    tags        TEXT DEFAULT '',        -- 标签（逗号分隔）
    sort_order  INTEGER DEFAULT 0,      -- 排序权重（越大越靠前）
    is_active   INTEGER DEFAULT 1,      -- 是否显示（软删除）
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 文章表（posts）

```sql
CREATE TABLE posts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT NOT NULL,          -- 文章标题
    slug        TEXT UNIQUE NOT NULL,   -- URL别名（如 sora-tutorial-2026）
    content     TEXT NOT NULL,          -- HTML内容 / Markdown
    excerpt     TEXT DEFAULT '',        -- 摘要
    cover       TEXT DEFAULT '',        -- 封面图URL
    status      TEXT DEFAULT 'published', -- published / draft
    view_count  INTEGER DEFAULT 0,     -- 阅读次数
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 2.3 友链表（links）

```sql
CREATE TABLE links (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,          -- 站点名称
    url         TEXT NOT NULL,          -- 站点链接
    description TEXT DEFAULT '',        -- 站点描述
    logo        TEXT DEFAULT '',        -- 图标/Logo
    email       TEXT DEFAULT '',        -- 站长邮箱（用于联系）
    sort_order  INTEGER DEFAULT 0,
    is_active   INTEGER DEFAULT 1,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 2.4 访问统计表（stats）

```sql
CREATE TABLE stats (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    page        TEXT DEFAULT '/',       -- 页面路径
    ip          TEXT DEFAULT '',        -- 访问IP
    user_agent  TEXT DEFAULT '',        -- UA
    referer     TEXT DEFAULT '',        -- 来源
    type        TEXT DEFAULT 'pv',      -- pv / uv
    tool_id     INTEGER DEFAULT NULL,   -- 点击的工具ID（用于工具点击排行）
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 2.5 管理员表（admins）

```sql
CREATE TABLE admins (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT UNIQUE NOT NULL,
    password    TEXT NOT NULL,          -- bcrypt哈希
    role        TEXT DEFAULT 'editor',  -- admin / editor
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 2.6 系统配置表（settings）

```sql
CREATE TABLE settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL
);
-- 预置: site_name, site_desc, beian, etc.
```

---

## 三、后台页面布局

### 整体框架

```
+-------------------------------------------+
|  🧭 djbaozi 后台管理系统     [用户名] [退出] |
+--------+----------------------------------+
|        |                                  |
|  📊 仪表盘  |  [主内容区域]                |
|  🔧 工具管理 |                              |
|  📝 文章管理 |   动态加载内容                |
|  🤝 友链管理 |                              |
|  📈 统计看板 |                              |
|  ⚙️ 系统设置 |                              |
|  📥 数据导入 |                              |
|  👤 管理员   |                              |
|        |                                  |
+--------+----------------------------------+
```

### 页面说明

| 页面 | URL | 功能 |
|------|-----|------|
| 登录页 | `/admin/login` | 管理员登录 |
| 仪表盘 | `/admin` | 概览：工具数/文章数/今日PV |
| 工具列表 | `/admin/tools` | 表格展示，搜索筛选，批量操作 |
| 工具编辑 | `/admin/tools/edit/<id>` | 表单增改 |
| 工具新增 | `/admin/tools/add` | 新建工具表单 |
| 文章列表 | `/admin/posts` | 表格+状态筛选 |
| 文章编辑 | `/admin/posts/edit/<id>` | 富文本编辑器 |
| 文章新增 | `/admin/posts/add` | 新建文章 |
| 友链管理 | `/admin/links` | 增删改+审核 |
| 统计看板 | `/admin/stats` | 图表：PV/UV/排行 |
| 数据导入 | `/admin/import` | CSV/JSON上传 |
| 数据导出 | `/admin/export` | CSV/JSON下载 |
| 管理员管理 | `/admin/admins` | 增删管理员 |
| 系统设置 | `/admin/settings` | 站点名称/备案号/SEO等 |

---

## 四、功能模块详细设计

### 4.1 工具CRUD管理

**功能列表：**
- ✅ 工具列表页：分页表格，搜索（名称/分类/标签），按分类筛选
- ✅ 新增工具：表单（名称* / 图标 / 描述 / 链接* / 分类* / 标签 / 排序）
- ✅ 编辑工具：同新增，预填充数据
- ✅ 删除工具：软删除（is_active=0），可回收站恢复
- ✅ 批量操作：批量删除、批量修改分类
- ✅ 排序拖拽：可手动输入排序值

**字段验证规则：**
- 名称：必填，最长50字符
- 链接：必填，合法URL
- 分类：从现有分类中选择，或输入新分类
- 图标：可选，Emoji / Font Awesome class / 图片URL
- 排序：整数，越大越靠前

### 4.2 文章管理

**功能列表：**
- ✅ 文章列表：分页表格，状态标签（已发布/草稿），搜索
- ✅ 发布文章：标题 / 别名slug（自动生成） / 内容（Markdown编辑器或富文本）
- ✅ 编辑文章：支持修改状态
- ✅ 删除文章：软删除或物理删除
- ✅ 预览功能：在新标签页查看文章效果
- ✅ Markdown支持：用 simplemde / editor.md 等轻量编辑器

**文章内容格式：**
- 推荐用 Markdown 存储，前端渲染为HTML
- 支持插入图片，自动上传到 `uploads/` 目录
- 自动生成摘要（截取前200字符）

### 4.3 统计看板

**数据采集方案：**
- 前端埋点：在index.html插入一段JS脚本，请求 `/api/track?type=pv&page=/`
- 工具点击追踪：工具链接改为 `/go/<tool_id>`，302跳转 + 记录点击
- 用 localStorage + 每日首次访问标记 区分PV/UV

**看板内容：**
```
┌─────────────────┬─────────────────┬─────────────────┐
│  今日PV: 1,234   │  今日UV: 567    │  在线工具: 45个   │
├─────────────────┴─────────────────┴─────────────────┤
│  📊 PV/UV趋势图（近7天/30天折线图）                   │
├─────────────────┬───────────────────────────────────┤
│  🔥 工具点击排行  │  📈 分类热度分布（饼图/柱状图）     │
│  1. Sora         │  - 视频生成: 45%                 │
│  2. Runway       │  - 图像生成: 30%                 │
│  3. Pika         │  - 文本工具: 15%                 │
└─────────────────┴───────────────────────────────────┘
```

**图表库推荐：** Chart.js（最轻量，CDN引入，无需npm）

### 4.4 友链管理

**功能列表：**
- ✅ 友链列表：表格展示，审核状态（待审核/已通过/已拒绝）
- ✅ 新增友链：名称 / URL / 描述 / Logo / 邮箱（自动提交申请）
- ✅ 审核功能：管理员审核通过/拒绝
- ✅ 排序功能：自定义排序权重
- ✅ 前端展示：自动渲染到首页友链区域

### 4.5 数据批量导入导出

**导出功能：**
- 导出工具数据为 CSV 或 JSON
- 导出文章数据为 CSV 或 JSON
- 支持按分类筛选后导出

**导入功能：**
- 上传 CSV / JSON 文件
- 预览数据（显示前5行）
- 字段映射（自动识别列名）
- 冲突处理策略：跳过 / 覆盖 / 新增
- 导入结果报告（成功N条，失败M条）

**CSV格式示例（工具）：**
```csv
name,icon,description,url,category,tags,sort_order
Sora,🎬,OpenAI视频生成,https://sora.com,视频生成,AI视频,10
Runway,🎥,专业AI视频编辑,https://runwayml.com,视频生成,AI视频/编辑,9
```

**JSON格式示例（工具）：**
```json
[
  {"name":"Sora","icon":"🎬","description":"OpenAI视频生成","url":"https://sora.com","category":"视频生成","tags":"AI视频","sort_order":10}
]
```

### 4.6 管理员权限控制

**角色设计：**

| 权限 | admin（超级管理员） | editor（编辑） |
|------|-------------------|----------------|
| 工具管理 CRUD | ✅ | ✅ |
| 文章管理 CRUD | ✅ | ✅ |
| 友链审核 | ✅ | ❌ |
| 管理员管理 | ✅ | ❌ |
| 系统设置 | ✅ | ❌ |
| 数据导入导出 | ✅ | ✅ |
| 查看统计 | ✅ | ✅ |

**安全措施：**
- 密码用 bcrypt 哈希存储
- Flask session 管理登录态（24h过期）
- 所有后台路由需要登录检查装饰器 `@login_required`
- CSRF 保护（Flask-WTF）
- XSS 防护（Jinja2自动转义）
- 操作日志记录（可选）

### 4.7 首页数据同步

**核心机制：** 后台数据修改后，自动重新生成 `index.html`

**方案A（推荐）：Jinja2模板渲染**
- 首页用Jinja2模板 `templates/index.html`
- 访问 `/` 时动态从SQLite读取数据渲染
- 无需手动生成静态文件，始终最新

**方案B：静态化（适合高流量）**
- 后台修改数据后，触发 `generate_index()` 函数
- 重新生成 `index.html` 静态文件
- 定时任务（cron）每日重新生成

**迁移建议：** 先用方案A，后期流量大了切方案B

---

## 五、项目目录结构

```
/Users/mac/Desktop/aivideo-nav/
├── app.py                    # Flask主入口
├── config.py                 # 配置文件
├── requirements.txt          # Python依赖
├── seed.py                   # 初始化数据库+种子数据
│
├── database/
│   └── nav.db                # SQLite数据库文件
│
├── models/
│   ├── __init__.py
│   ├── tool.py               # 工具模型
│   ├── post.py               # 文章模型
│   ├── link.py               # 友链模型
│   ├── stats.py              # 统计模型
│   └── admin.py              # 管理员模型
│
├── routes/
│   ├── __init__.py
│   ├── auth.py               # 登录/登出
│   ├── tools.py              # 工具管理
│   ├── posts.py              # 文章管理
│   ├── links.py              # 友链管理
│   ├── stats.py              # 统计API
│   ├── admin_users.py        # 管理员管理
│   ├── settings.py           # 系统设置
│   └── import_export.py      # 导入导出
│
├── templates/
│   ├── admin/
│   │   ├── base.html         # 后台布局模板
│   │   ├── login.html        # 登录页
│   │   ├── dashboard.html    # 仪表盘
│   │   ├── tools_list.html   # 工具列表
│   │   ├── tools_form.html   # 工具表单
│   │   ├── posts_list.html   # 文章列表
│   │   ├── posts_form.html   # 文章表单
│   │   ├── links_list.html   # 友链列表
│   │   ├── links_form.html   # 友链表单
│   │   ├── stats.html        # 统计看板
│   │   ├── import.html       # 导入页面
│   │   ├── export.html       # 导出页面
│   │   ├── admins.html       # 管理员管理
│   │   └── settings.html     # 系统设置
│   └── frontend/
│       ├── index.html        # 首页模板（Jinja2）
│       └── post.html         # 文章详情模板
│
├── static/
│   ├── admin.css             # 后台样式
│   ├── admin.js              # 后台JS
│   └── uploads/              # 上传文件
│
├── posts/                    # [保留] 原有静态文章
└── scripts/
    └── gen-article.py        # [保留] 原有脚本
```

---

## 六、实现计划（分阶段）

### 第一阶段：MVP（1天）
1. 搭Flask骨架 + SQLite初始化
2. 工具CRUD（增删改查）
3. 管理员登录
4. 后台布局模板
5. 首页动态渲染（从数据库读工具列表）

### 第二阶段：内容管理（1天）
6. 文章管理（Markdown编辑器）
7. 友链管理（含申请表单）
8. 数据导入导出（CSV/JSON）

### 第三阶段：统计与完善（1天）
9. 统计埋点JS + 统计看板（Chart.js）
10. 系统设置页
11. 权限控制细化
12. 原有静态数据迁移脚本

---

## 七、快速启动命令

```bash
# 1. 安装依赖
cd /Users/mac/Desktop/aivideo-nav
pip install flask flask-login flask-sqlalchemy bcrypt python-dotenv

# 2. 初始化数据库
python seed.py

# 3. 启动
python app.py
# 访问 http://localhost:5000/admin
# 默认管理员账号 admin / admin123
```

---

## 八、关键设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 数据库 | SQLite | 单文件，零运维 |
| ORM | Flask-SQLAlchemy | 成熟，可迁移到MySQL |
| 前端框架 | Bootstrap 5 | 轻量，CDN引入 |
| 富文本编辑器 | Editor.md（Markdown） | 轻量，GitHub风格 |
| 图表 | Chart.js | CDN引入，无需npm |
| 认证 | Flask-Login + bcrypt | 成熟方案 |
| 部署 | Gunicorn + systemd 或 直接python | 简单 |

---

## 九、数据迁移策略（从静态页面到后台）

1. 解析当前 `index.html` 中的工具列表（按DOM结构提取）
2. 将提取的数据写入 `tools` 表
3. 解析 `posts/` 目录下的HTML文章，写入 `posts` 表
4. 生成的 `index.html` 改为Jinja2模板
5. 设置URL重写，原有文章URL依然可用

**迁移脚本（seed.py）主要功能：**
- 爬取当前 index.html 的工具卡片结构
- 识别分类（取现有分类）
- 识别标签
- 写入SQLite
- 创建默认管理员账号
