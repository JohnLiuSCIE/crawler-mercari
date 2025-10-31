# 日本二手抱枕套自动化爬虫系统
# Japanese Dakimakura Secondhand Market Scraper

自动监控日本二手市场（Mercari、Yahoo拍卖、骏河屋、Lashinbang）上的特定抱枕套商品。

## 功能特点

- 🔍 **多平台搜索**: 支持4个主流日本二手平台
  - Mercari (メルカリ)
  - Yahoo! Auction / PayPay Flea Market (ヤフオク / PayPayフリマ)
  - Suruga-ya (駿河屋)
  - Lashinbang (らしんばん)

- 📊 **智能状态检测**:
  - ✅ 在售商品（可购买）
  - 🔄 已售商品（最近售价）
  - ❌ 未找到

- 📧 **自动通知**: 发现新商品或价格变化时发送邮件

- 👥 **创作者监控**: 追踪社团/绘师的新品发布和再版消息

- 🕐 **定时任务**: 每天自动运行1-2次

## 项目结构

```
scraper/
├── config/
│   ├── items.yaml          # 监控的商品配置
│   ├── platforms.yaml      # 平台配置
│   └── settings.py         # 全局设置
├── adapters/
│   ├── base_adapter.py     # 基础适配器类
│   ├── mercari.py          # Mercari适配器
│   ├── yahoo_auction.py    # Yahoo拍卖适配器
│   ├── surugaya.py         # 骏河屋适配器
│   └── lashinbang.py       # Lashinbang适配器
├── models/
│   └── database.py         # 数据库模型
├── utils/
│   └── logger.py           # 日志工具
├── test_mercari.py         # Mercari测试脚本
├── requirements.txt
└── README.md
```

## 快速开始

### 1. 安装依赖

```bash
# 创建虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 安装Playwright浏览器
playwright install chromium
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑.env文件，填入你的配置
nano .env
```

必填配置项：
```bash
# 邮件通知配置
EMAIL_ENABLED=true
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=recipient@example.com
```

### 3. 测试 Mercari 适配器

```bash
# 运行Mercari测试脚本
python test_mercari.py
```

这将：
1. 初始化Mercari适配器
2. 搜索第一个配置的商品（神里绫华抱枕套）
3. 打开搜索结果中的商品详情页
4. 提取价格、状态等信息
5. 显示结果摘要

### 4. 自定义监控商品

编辑 `config/items.yaml` 文件来配置你想监控的商品：

```yaml
items:
  - id: 1
    name_cn: "神里绫华 抱枕套"
    name_jp: "神里綾華 抱き枕カバー"
    series: "原神"
    character: "神里綾華"
    circle: "MILK BAR"
    event: "C100"
    artist: "シロガネヒナ"
    search_keywords:
      - "神里綾華 抱き枕 MILK BAR"
      - "神里綾華 抱き枕 シロガネヒナ"
```

## 当前已配置的商品

1. 【原神】神里綾華 抱き枕カバー（MILK BAR、C100、シロガネヒナ）
2. 【原神】ナヒーダ 抱き枕カバー（MILK BAR、C101、シロガネヒナ）
3. 【原神】瑞希／夢見月瑞希 抱き枕カバー（鳩小屋／鳩春、俺の嫁！伍拾）
4. 【崩壊：スターレイル】キャストリス 抱き枕カバー（MILK BAR、C106、シロガネヒナ）
5. 【原神】千織 抱き枕カバー（鳩小屋／鳩春）
6. 【崩壊：スターレイル】キャストリス 抱き枕カバー（Royalみるく、C106）
7. 【原神】バーバラ 抱き枕カバー（Dragon Kitchen、さそりがため）

## 测试状态

### ✅ 已实现
- [x] 项目结构搭建
- [x] 配置系统
- [x] 数据库模型
- [x] 基础适配器类
- [x] Mercari适配器
- [x] 测试脚本

### 🚧 进行中
- [ ] Yahoo拍卖适配器（已创建，待测试）
- [ ] 骏河屋适配器（已创建，待测试）
- [ ] Lashinbang适配器（已创建，待测试）

### 📋 待开发
- [ ] 报告生成器（4x7表格）
- [ ] 邮件通知系统
- [ ] 创作者监控模块
- [ ] 变化检测引擎
- [ ] 定时调度器
- [ ] 主程序入口

## 开发计划

### 第一阶段：Mercari测试
1. ✅ 实现Mercari适配器
2. ✅ 创建测试脚本
3. ⏳ 运行测试并验证结果
4. ⏳ 根据测试结果调整选择器和匹配逻辑

### 第二阶段：其他平台
1. 测试Yahoo拍卖适配器
2. 测试骏河屋适配器
3. 测试Lashinbang适配器
4. 优化各平台的爬取逻辑

### 第三阶段：完整系统
1. 实现报告生成器
2. 实现邮件通知
3. 添加创作者监控
4. 集成定时调度
5. 完整测试

## 注意事项

### 反爬虫策略
- 使用Playwright模拟真实浏览器
- 随机延迟请求
- 轮换User-Agent
- 遵守robots.txt
- 速率限制

### 海外访问
如果你在日本境外运行，某些网站可能限制访问：
- 先尝试不使用代理
- 如果被限制，配置日本代理服务器
- 在 `config/platforms.yaml` 中设置代理

### Gmail SMTP设置
如果使用Gmail发送通知：
1. 启用两步验证
2. 生成应用专用密码
3. 在.env中使用应用密码而非账号密码

## 故障排除

### 问题：Playwright无法启动浏览器
```bash
# 重新安装浏览器
playwright install chromium
```

### 问题：找不到模块
```bash
# 确保在项目根目录运行
cd /path/to/scraper
python test_mercari.py
```

### 问题：无法提取商品信息
- 网站可能更新了HTML结构
- 检查日志中的错误信息
- 可能需要更新CSS选择器

## 许可证

本项目仅供个人学习和合法使用。请遵守各平台的服务条款。

## 反馈

如有问题或建议，请创建Issue。