#!/bin/bash
# 启动高德地图 MCP 服务（英文版）

# 停止旧的服务
pkill -f "amap-maps-mcp-server"
sleep 2

# 启动新服务
cd /root
nohup /root/miniconda3/envs/OpenWebUI/bin/uvx mcpo \
  --port 9001 \
  --server-type "streamable-http" \
  -- env AMAP_MAPS_API_KEY="db2bb74f229bb19058b4ab85350a2c85" \
     npx @amap/amap-maps-mcp-server \
  > /tmp/amap_mcp.log 2>&1 &

echo "高德地图 MCP 服务已启动（端口 9001）"
echo "查看日志: tail -f /tmp/amap_mcp.log"
echo ""
echo "等待 5 秒后测试服务..."
sleep 5

# 测试服务
if curl -s http://localhost:9001/tools > /dev/null 2>&1; then
    echo "✅ 服务启动成功！"
    echo ""
    echo "在 Open WebUI 中配置："
    echo "  URL: http://localhost:9001"
    echo "  API Key: db2bb74f229bb19058b4ab85350a2c85"
else
    echo "❌ 服务启动失败，查看日志:"
    tail -20 /tmp/amap_mcp.log
fi

