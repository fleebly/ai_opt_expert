# 部署指南 - Netlify + Railway

本文档说明如何将量化交易策略管理平台部署到 Netlify 和 Railway。

## 📋 部署架构

- **Railway**: 部署 Streamlit 后端应用（主要服务）
- **Netlify**: 部署静态前端页面，重定向到 Railway 服务

## 🚂 Railway 部署

Railway 是部署 Streamlit 应用的主要平台。

### 方法 1: 使用 Docker（推荐）

1. **登录 Railway**
   ```bash
   # 访问 https://railway.app
   # 使用 GitHub 账号登录
   ```

2. **创建新项目**
   - 点击 "New Project"
   - 选择 "Deploy from GitHub repo"
   - 选择你的仓库

3. **配置环境变量**
   在 Railway 项目设置中添加以下环境变量：
   ```
   POLYGON_API_KEY=your_polygon_api_key
   DEEPSEEK_API_KEY=your_deepseek_api_key
   PORT=8501
   ```

4. **配置部署**
   - Railway 会自动检测 `Dockerfile`
   - 或使用 `railway.json` 配置文件
   - 确保端口设置为 `$PORT`（Railway 会自动分配）

5. **启动命令**
   Railway 会自动使用 Dockerfile 中的配置，或使用 Procfile：
   ```bash
   streamlit run web_app.py --server.port $PORT --server.address 0.0.0.0 --server.headless true
   ```

### 方法 2: 使用 Python Buildpack

1. **创建项目**（同上）
2. **Railway 会自动检测 Python 项目**
3. **设置启动命令**：
   ```
   streamlit run web_app.py --server.port $PORT --server.address 0.0.0.0
   ```

### 环境变量配置

在 Railway Dashboard 的 Variables 标签页添加：

| 变量名 | 说明 | 必需 |
|--------|------|------|
| `POLYGON_API_KEY` | Polygon.io API 密钥 | 是 |
| `DEEPSEEK_API_KEY` | DeepSeek AI API 密钥 | 是 |
| `PORT` | 服务端口（Railway 自动设置） | 否 |

### 获取 Railway URL

部署完成后，Railway 会提供一个公共 URL，例如：
```
https://your-app-name.railway.app
```

**重要**: 将此 URL 更新到 `netlify.toml` 和 `public/index.html` 中。

---

## 🌐 Netlify 部署

Netlify 主要用于部署静态前端页面，提供重定向到 Railway 服务。

### 部署步骤

1. **登录 Netlify**
   ```bash
   # 访问 https://netlify.com
   # 使用 GitHub 账号登录
   ```

2. **创建新站点**
   - 点击 "Add new site" -> "Import an existing project"
   - 选择你的 GitHub 仓库
   - 选择分支（通常是 `main` 或 `master`）

3. **配置构建设置**
   - **Build command**: 留空或使用 `echo "Static site"`
   - **Publish directory**: `public`
   - **Base directory**: 留空（根目录）

4. **更新重定向 URL**
   编辑 `netlify.toml`，将 `your-app-name.railway.app` 替换为你的实际 Railway URL：
   ```toml
   [[redirects]]
     from = "/*"
     to = "https://your-actual-railway-url.railway.app"
     status = 200
   ```

5. **部署**
   - 点击 "Deploy site"
   - Netlify 会自动构建并部署

### 自定义域名（可选）

在 Netlify Dashboard:
1. 进入 Site settings -> Domain management
2. 添加自定义域名
3. 配置 DNS 记录

---

## 🔧 本地测试

### 测试 Railway 配置

```bash
# 使用 Docker 本地测试
docker build -t ai-opt-expert .
docker run -p 8501:8501 \
  -e POLYGON_API_KEY=your_key \
  -e DEEPSEEK_API_KEY=your_key \
  ai-opt-expert

# 访问 http://localhost:8501
```

### 测试 Netlify 配置

```bash
# 安装 Netlify CLI
npm install -g netlify-cli

# 本地预览
netlify dev

# 访问 http://localhost:8888
```

---

## 📝 部署检查清单

### Railway 部署前
- [ ] 环境变量已配置（POLYGON_API_KEY, DEEPSEEK_API_KEY）
- [ ] Dockerfile 已测试通过
- [ ] `railway.json` 或 `Procfile` 配置正确
- [ ] 端口使用 `$PORT` 环境变量

### Netlify 部署前
- [ ] `public/index.html` 存在
- [ ] `netlify.toml` 中的 Railway URL 已更新
- [ ] 静态资源已准备好

### 部署后验证
- [ ] Railway 应用可以访问
- [ ] Streamlit 界面正常显示
- [ ] 环境变量正常工作
- [ ] Netlify 重定向到 Railway
- [ ] 所有功能正常（优化、扫描、管理等）

---

## 🐛 常见问题

### Railway 部署失败

1. **端口问题**
   - 确保使用 `$PORT` 环境变量
   - 检查启动命令是否正确

2. **依赖安装失败**
   - 检查 `requirements.txt` 是否完整
   - 查看构建日志

3. **应用无法启动**
   - 检查环境变量是否配置
   - 查看 Railway 日志

### Netlify 重定向失败

1. **URL 未更新**
   - 确保 `netlify.toml` 中的 URL 正确
   - 确保 `public/index.html` 中的 URL 正确

2. **构建失败**
   - 检查 `public/` 目录是否存在
   - 检查 `.netlifyignore` 配置

---

## 🔗 相关链接

- [Railway 文档](https://docs.railway.app/)
- [Netlify 文档](https://docs.netlify.com/)
- [Streamlit 部署指南](https://docs.streamlit.io/streamlit-cloud/deploy-your-app)

---

## 📞 支持

如有问题，请检查：
1. Railway 部署日志
2. Netlify 构建日志
3. 应用运行时日志

---

**最后更新**: 2025-11-06

