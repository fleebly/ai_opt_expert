#!/bin/bash

# 部署脚本 - Netlify + Railway

set -e

echo "🚀 部署配置检查脚本"
echo "===================="
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查必要的文件
echo "📋 检查部署文件..."

files=(
    "Dockerfile"
    "docker-entrypoint.sh"
    "railway.json"
    "Procfile"
    "netlify.toml"
    "public/index.html"
    "DEPLOYMENT.md"
)

missing_files=()

for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅${NC} $file"
    else
        echo -e "${RED}❌${NC} $file (缺失)"
        missing_files+=("$file")
    fi
done

echo ""

if [ ${#missing_files[@]} -gt 0 ]; then
    echo -e "${RED}错误: 以下文件缺失:${NC}"
    printf '%s\n' "${missing_files[@]}"
    exit 1
fi

# 检查 docker-entrypoint.sh 权限
if [ -f "docker-entrypoint.sh" ]; then
    if [ ! -x "docker-entrypoint.sh" ]; then
        echo -e "${YELLOW}⚠️${NC} 设置 docker-entrypoint.sh 执行权限..."
        chmod +x docker-entrypoint.sh
    fi
fi

# 检查环境变量配置提示
echo ""
echo "🔑 环境变量配置检查:"
echo ""

if [ -z "$POLYGON_API_KEY" ]; then
    echo -e "${YELLOW}⚠️${NC} POLYGON_API_KEY 未设置（需要在 Railway 中配置）"
else
    echo -e "${GREEN}✅${NC} POLYGON_API_KEY 已设置"
fi

if [ -z "$DEEPSEEK_API_KEY" ]; then
    echo -e "${YELLOW}⚠️${NC} DEEPSEEK_API_KEY 未设置（需要在 Railway 中配置）"
else
    echo -e "${GREEN}✅${NC} DEEPSEEK_API_KEY 已设置"
fi

# 检查 Netlify 配置中的 Railway URL
echo ""
echo "🌐 检查 Netlify 配置..."
if grep -q "your-app-name.railway.app" netlify.toml; then
    echo -e "${YELLOW}⚠️${NC} netlify.toml 中的 Railway URL 需要更新"
    echo "   请将 'your-app-name.railway.app' 替换为实际的 Railway URL"
else
    echo -e "${GREEN}✅${NC} netlify.toml 配置看起来正确"
fi

if grep -q "your-app-name.railway.app" public/index.html; then
    echo -e "${YELLOW}⚠️${NC} public/index.html 中的 Railway URL 需要更新"
else
    echo -e "${GREEN}✅${NC} public/index.html 配置看起来正确"
fi

echo ""
echo "📝 下一步:"
echo "1. 在 Railway 中创建新项目并连接 GitHub 仓库"
echo "2. 配置环境变量: POLYGON_API_KEY, DEEPSEEK_API_KEY"
echo "3. 获取 Railway URL 并更新 netlify.toml 和 public/index.html"
echo "4. 在 Netlify 中创建新站点并连接 GitHub 仓库"
echo "5. 查看 DEPLOYMENT.md 获取详细说明"
echo ""
echo -e "${GREEN}✅ 部署配置检查完成!${NC}"

