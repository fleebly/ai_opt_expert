# 快速部署指南

## 🚀 一键部署到 Railway + Netlify

### Railway 部署（5分钟）

1. **登录 Railway**
   - 访问 https://railway.app
   - 使用 GitHub 账号登录

2. **创建项目**
   ```
   New Project → Deploy from GitHub repo
   → 选择你的仓库
   ```

3. **配置环境变量**
   在 Railway Dashboard → Variables 中添加：
   ```
   POLYGON_API_KEY=你的密钥
   DEEPSEEK_API_KEY=你的密钥
   ```

4. **部署完成**
   - Railway 会自动检测 Dockerfile 并部署
   - 获取你的 Railway URL（例如：`your-app.railway.app`）

### Netlify 部署（3分钟）

1. **登录 Netlify**
   - 访问 https://netlify.com
   - 使用 GitHub 账号登录

2. **创建站点**
   ```
   Add new site → Import an existing project
   → 选择你的仓库
   ```

3. **配置构建**
   - Build command: 留空
   - Publish directory: `public`

4. **更新重定向 URL**
   - 编辑 `netlify.toml`，将 `your-app-name.railway.app` 替换为你的 Railway URL
   - 编辑 `public/index.html`，同样更新 URL

5. **重新部署**
   - Netlify 会自动重新部署

### ✅ 验证部署

1. 访问 Netlify URL - 应该重定向到 Railway
2. 访问 Railway URL - 应该显示 Streamlit 应用
3. 测试应用功能是否正常

### 📚 详细文档

查看 [DEPLOYMENT.md](./DEPLOYMENT.md) 获取完整部署说明。

