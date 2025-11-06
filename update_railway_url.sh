#!/bin/bash

# 更新 Railway URL 配置脚本

echo "🚂 更新 Railway URL 配置"
echo "========================"
echo ""

# 检查是否提供了 URL 参数
if [ -n "$1" ]; then
    RAILWAY_URL="$1"
else
    echo "请输入你的 Railway 应用 URL"
    echo "例如: https://your-app-name.railway.app"
    echo ""
    read -p "Railway URL: " RAILWAY_URL
fi

if [ -z "$RAILWAY_URL" ]; then
    echo "❌ 未提供 URL，退出"
    exit 1
fi

# 清理 URL（移除尾部斜杠和协议）
RAILWAY_DOMAIN=$(echo "$RAILWAY_URL" | sed 's|https\?://||' | sed 's|/$||')

echo "📝 更新配置..."
echo "   Railway URL: $RAILWAY_URL"
echo "   Domain: $RAILWAY_DOMAIN"
echo ""

# 更新 netlify.toml
if [ -f "netlify.toml" ]; then
    # 备份原文件
    cp netlify.toml netlify.toml.bak
    
    # 更新 URL
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|https://your-app-name.railway.app|$RAILWAY_URL|g" netlify.toml
        sed -i '' "s|your-app-name.railway.app|$RAILWAY_DOMAIN|g" netlify.toml
    else
        # Linux
        sed -i "s|https://your-app-name.railway.app|$RAILWAY_URL|g" netlify.toml
        sed -i "s|your-app-name.railway.app|$RAILWAY_DOMAIN|g" netlify.toml
    fi
    
    echo "✅ netlify.toml 已更新"
else
    echo "❌ netlify.toml 文件不存在"
fi

# 更新 public/index.html
if [ -f "public/index.html" ]; then
    # 备份原文件
    cp public/index.html public/index.html.bak
    
    # 更新 URL
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|https://your-app-name.railway.app|$RAILWAY_URL|g" public/index.html
        sed -i '' "s|'https://your-app-name.railway.app'|'$RAILWAY_URL'|g" public/index.html
    else
        # Linux
        sed -i "s|https://your-app-name.railway.app|$RAILWAY_URL|g" public/index.html
        sed -i "s|'https://your-app-name.railway.app'|'$RAILWAY_URL'|g" public/index.html
    fi
    
    echo "✅ public/index.html 已更新"
else
    echo "❌ public/index.html 文件不存在"
fi

echo ""
echo "✅ 配置更新完成！"
echo ""
echo "📋 下一步:"
echo "   1. 检查更新后的配置:"
echo "      cat netlify.toml | grep -A 2 redirects"
echo ""
echo "   2. 重新部署到 Netlify:"
echo "      netlify deploy --dir=public --prod"
echo ""


