#!/bin/bash

# 启动 When.Trade 后端服务

# 颜色
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}启动 When.Trade 后端服务...${NC}"

# 设置环境变量
export PYTHONPATH="$(pwd)"
export DEVELOPMENT=true

# 检查端口
if lsof -i:8000 > /dev/null 2>&1; then
    echo -e "${RED}错误: 端口 8000 已被占用${NC}"
    echo "请先运行 ./stop.sh 停止现有服务"
    exit 1
fi

# 检查数据库
if ! lsof -i:5432 > /dev/null 2>&1; then
    echo -e "${RED}警告: PostgreSQL 未运行 (端口 5432)${NC}"
fi

if ! lsof -i:6379 > /dev/null 2>&1; then
    echo -e "${RED}警告: Redis 未运行 (端口 6379)${NC}"
fi

# 使用 whentrade 环境的 Python 启动
echo -e "${GREEN}启动 FastAPI...${NC}"
/opt/anaconda3/envs/whentrade/bin/python -m uvicorn core.main:app --reload --host 0.0.0.0 --port 8000