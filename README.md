# Yoasobi Scraper

爬虫项目，用于抓取 Yoasobi Heaven 网站的博客文章，支持自动翻译并推送到 Notion。

## ✨ 功能特性

- 🔍 通过API抓取博客文章
- 🖼️ **支持图片和视频封面下载**（包括防盗链保护）
- 📹 **自动检测并下载MP4/WebM视频内容**
- 🌏 自动翻译日文到简体中文
- 📝 推送到 Notion 数据库
- 💾 本地数据存储（避免重复抓取）
- 🔄 支持 Backfill 模式扫描所有页面

## 🎥 视频支持

本爬虫已增强，完全支持视频内容：

- ✅ **视频封面检测**：自动识别 `.mp4`, `.mov`, `.avi`, `.webm` 格式的封面
- ✅ **防盗链绕过**：使用正确的 Referer 头下载受保护的视频
- ✅ **Notion优化**：视频自动添加到页面内容顶部
- ✅ **智能处理**：Image属性优雅降级（视频封面时使用首张图片）

## 🚀 快速开始

### 环境要求

- Python 3.12+
- uv 或 pip

### 安装依赖

```bash
# 使用 uv (推荐)
uv sync

# 或使用 pip
pip install -r requirements.txt
```

### 配置

1. **设置年龄验证**（必需）：
   - 已自动设置 `age_checked` cookie

2. **VIP内容访问**（可选）：
   ```bash
   export YOASOBI_COOKIES="PHPSESSID=xxx; other_cookie=yyy"
   ```

3. **Notion集成**（可选）：
   ```bash
   export NOTION_TOKEN="secret_xxx"
   export NOTION_DATABASE_ID="your-database-id"
   export GITHUB_REPOSITORY="username/repo"  # 用于图片托管
   ```

### 运行爬虫

```bash
# 标准模式（增量抓取）
python scraper.py

# Backfill 模式（扫描所有页面）
BACKFILL=true python scraper.py
```

## 🧪 测试

### 测试单篇文章

使用测试脚本验证特定文章（包括视频内容）：

```bash
python test_single_article.py
```

测试脚本会：
- 搜索目标文章或带视频封面的文章
- 下载图片和视频到 `./images/`
- 翻译并处理内容
- 输出到 `test_output.json`
- 可选推送到 Notion（如果配置了环境变量）

### 演示视频封面处理

查看视频封面检测和处理逻辑：

```bash
python demo_video_cover.py
```

## 📁 项目结构

```
yoasobi-scraper/
├── scraper.py              # 主爬虫脚本
├── test_single_article.py  # 单文章测试脚本
├── demo_video_cover.py     # 视频封面演示
├── params.json             # API 参数配置
├── data_store.json         # 本地数据存储
├── images/                 # 下载的图片和视频
└── requirements.txt        # 依赖列表
```

## 🔧 API 参数

`params.json` 包含API请求参数，可以自定义：

```json
{
  "c_commu_id": "xxx",
  "c_area_id": "xxx",
  "c_shop_id": "xxx",
  "c_member_id": "xxx"
}
```

## 📊 数据格式

每篇文章存储为：

```json
{
  "id": "文章ID",
  "title": "标题",
  "cover_filename": "封面文件名",
  "cover_type": "image 或 video",
  "original_text": "原文（日文）",
  "translated_text": "译文（中文）",
  "timestamp": 1234567890,
  "content_blocks": [
    {"type": "video", "filename": "xxx.mp4", "is_cover": true},
    {"type": "heading_2", "content": "标题"},
    {"type": "text", "content": "文本内容"},
    {"type": "image", "filename": "xxx.jpg"}
  ]
}
```

## 🎯 Notion 数据库结构

推荐的 Notion 数据库属性：

| 属性名 | 类型 | 说明 |
|--------|------|------|
| Title | Title | 文章标题 |
| Date | Date | 发布日期（JST） |
| Content (JP) | Text | 日文原文（前2000字） |
| Content (CN) | Text | 中文译文（前2000字） |
| Original URL | URL | 原始封面URL |
| Image | Files | 封面图片（视频封面时为首张图片） |

## ⚠️ 注意事项

- **防盗链**：视频和部分图片有防盗链保护，需要正确的 Referer（已自动处理）
- **VIP内容**：部分内容需要登录，请设置 `YOASOBI_COOKIES` 环境变量
- **速率限制**：已内置延迟，避免请求过快
- **GitHub托管**：Notion需要公开URL，建议将 `images/` 推送到GitHub

## 🐛 故障排除

### 视频下载失败

确保：
1. ✅ 使用最新版本的代码（已包含防盗链修复）
2. ✅ 检查网络连接
3. ✅ 视频URL是否有效

### Notion 上传失败

确保：
1. ✅ `NOTION_TOKEN` 和 `NOTION_DATABASE_ID` 已设置
2. ✅ Token 有数据库写入权限
3. ✅ 数据库属性名称与代码匹配
4. ✅ `GITHUB_REPOSITORY` 已设置（用于图片URL）

### "Member Only" 警告

设置你的登录 cookies：
```bash
export YOASOBI_COOKIES="从浏览器复制的完整 Cookie 字符串"
```

## 📝 更新日志

### 2025-12-29
- ✅ **视频封面支持**：完整支持MP4等视频格式封面
- ✅ **防盗链修复**：添加 Referer 头绕过防盗链保护
- ✅ **Notion优化**：视频内容正确显示在页面中
- ✅ **测试工具**：添加单文章测试脚本

## 📄 License

MIT
