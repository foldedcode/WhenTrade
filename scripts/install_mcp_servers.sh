#!/bin/bash

# MCP服务器安装脚本
# 用于安装When.Trade所需的MCP服务器

echo "🚀 Installing MCP servers for When.Trade..."

# 检查是否安装了npm
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install Node.js and npm first."
    exit 1
fi

# 安装的MCP服务器列表
MCP_SERVERS=(
    "@modelcontextprotocol/server-filesystem"
    "@modelcontextprotocol/server-time"
    "@modelcontextprotocol/server-web-search"
    "@modelcontextprotocol/server-memory"
    "@modelcontextprotocol/server-sqlite"
)

# 可选的MCP服务器（需要额外配置）
OPTIONAL_SERVERS=(
    "@modelcontextprotocol/server-postgres"
    "@modelcontextprotocol/server-everart"
)

echo "📦 Installing required MCP servers..."
echo ""

# 安装必需的MCP服务器
for server in "${MCP_SERVERS[@]}"; do
    echo "Installing $server..."
    npm install -g "$server"
    if [ $? -eq 0 ]; then
        echo "✅ $server installed successfully"
    else
        echo "❌ Failed to install $server"
    fi
    echo ""
done

echo "📋 Required MCP servers installation complete!"
echo ""
echo "🔧 Optional MCP servers (install if needed):"
for server in "${OPTIONAL_SERVERS[@]}"; do
    echo "  - $server"
done
echo ""
echo "To install optional servers, run:"
echo "npm install -g <server-name>"
echo ""

# 创建MCP服务器配置目录
MCP_CONFIG_DIR="$HOME/.config/mcp"
if [ ! -d "$MCP_CONFIG_DIR" ]; then
    echo "📁 Creating MCP configuration directory..."
    mkdir -p "$MCP_CONFIG_DIR"
    echo "✅ Created $MCP_CONFIG_DIR"
fi

echo ""
echo "🎉 MCP server setup complete!"
echo ""
echo "📝 Next steps:"
echo "1. Set up environment variables in your .env file:"
echo "   - ANTHROPIC_API_KEY (for Claude integration)"
echo "   - OPENAI_API_KEY (for OpenAI integration)"
echo "   - GITHUB_TOKEN (for GitHub integration)"
echo ""
echo "2. Start the When.Trade backend:"
echo "   docker-compose -f docker-compose.dev.yml up -d"
echo ""
echo "3. The MCP servers will be automatically connected when the backend starts."