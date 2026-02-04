#!/bin/bash
# scripts/setup-remote.sh - Aden Agent Framework Remote Development Utility

echo ""
echo "==================================="
echo "  Remote Development Setup"
echo "==================================="
echo ""
echo "🚀 This script configures your environment for remote"
echo "   development via SSH (VS Code, Cursor, PyCharm)."
echo ""

# 1. Install networking dependencies
echo "📦 Installing openssh-server and net-tools..."
sudo apt update && sudo apt install -y openssh-server net-tools

# 2. Configure Firewall for SSH
echo "🛡️  Configuring Firewall..."
sudo ufw allow 22

# 3. Reload and Restart SSH service
echo "🔄 Refreshing SSH services..."
sudo systemctl daemon-reload
sudo systemctl restart ssh

echo ""
echo "✅ Setup Complete!"
echo "--------------------------------------------------------"
echo "💡 INSTRUCTIONS FOR YOUR HOST (Windows/Mac):"
echo "1. VirtualBox: Map Host Port 2222 to Guest Port 22."
echo "2. Your Internal IP is: $(hostname -I | awk '{print $1}')"
echo "3. Connection Command: ssh federico@127.0.0.1 -p 2222"
echo "--------------------------------------------------------"