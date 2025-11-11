#!/bin/bash
# 使用 conda 环境中修改后的 amap-mcp-server

# 设置 API Key
export AMAP_MAPS_API_KEY="your_api_key"

# 停止旧服务
pkill -f "amap-mcp-server" 2>/dev/null
sleep 2

# 使用 conda 环境中的 Python 直接运行
cd /root
nohup /root/miniconda3/envs/OpenWebUI/bin/python -m amap_mcp_server.server streamable-http \
  --port 9002 \
  > /tmp/amap_mcp_conda.log 2>&1 &

echo "✅ 高德地图 MCP 服务已启动（使用 conda 环境中的修改版本）"
echo "📍 端口: 9002"
echo "📝 日志: tail -f /tmp/amap_mcp_conda.log"
echo ""
echo "等待 5 秒后测试服务..."
sleep 5

# 测试服务
if curl -s http://localhost:9002/health > /dev/null 2>&1 || \
   curl -s http://localhost:9002/ > /dev/null 2>&1; then
    echo "✅ 服务启动成功！"
    echo ""
    echo "在 Open WebUI 中配置："
    echo "  URL: http://localhost:9002"
else
    echo "❌ 服务可能未正常启动，查看日志:"
    tail -20 /tmp/amap_mcp_conda.log
fi
