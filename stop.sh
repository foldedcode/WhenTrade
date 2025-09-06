#!/bin/bash

# 停止 When.Trade 后端服务

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}停止 When.Trade 后端服务...${NC}"

# 停止所有 uvicorn 进程
pkill -f "uvicorn core.main:app"

# 确认停止
if pgrep -f "uvicorn core.main:app" > /dev/null; then
    echo -e "${YELLOW}强制停止残留进程...${NC}"
    pkill -9 -f "uvicorn core.main:app"
fi

echo -e "${GREEN}服务已停止${NC}"

# 显示状态
if lsof -i:8000 > /dev/null 2>&1; then
    echo -e "${YELLOW}警告: 端口 8000 仍被占用${NC}"
    lsof -i:8000
else
    echo -e "${GREEN}端口 8000 已释放${NC}"
fi