#!/bin/bash

# Railway 部署脚本

echo "🚂 Railway 部署脚本"
echo "==================="
echo ""

# 检查是否已链接项目
if ! railway status &>/dev/null; then
    echo "❌ 项目未链接，正在初始化..."
    railway init --name ai-opt-expert
fi

echo "✅ 项目已链接"
echo ""

# 显示当前状态
echo "📊 当前项目状态:"
railway status
echo ""

# 检查环境变量
echo "🔍 检查环境变量..."
if railway variables 2>/dev/null | grep -q "POLYGON_API_KEY"; then
    echo "  ✅ POLYGON_API_KEY 已设置"
else
    echo "  ⚠️  POLYGON_API_KEY 未设置"
    echo "     运行: railway variables set POLYGON_API_KEY=your_key"
fi

if railway variables 2>/dev/null | grep -q "DEEPSEEK_API_KEY"; then
    echo "  ✅ DEEPSEEK_API_KEY 已设置"
else
    echo "  ⚠️  DEEPSEEK_API_KEY 未设置"
    echo "     运行: railway variables set DEEPSEEK_API_KEY=your_key"
fi

echo ""
echo "🚀 开始部署..."
echo ""

# 部署应用
railway up

echo ""
echo "✅ 部署完成！"
echo ""
echo "📋 后续操作:"
echo "  - 查看日志: railway logs"
echo "  - 查看状态: railway status"
echo "  - 获取 URL: railway domain"
echo ""


