#!/bin/bash

# 🚀 Pure VPN - Vercel Deployment Script
# This script deploys the frontend to Vercel while keeping backend on VPS

set -e

echo "🚀 Pure VPN - Vercel Deployment"
echo "==============================================="

# Check if we're in the right directory
if [ ! -d "frontend" ]; then
    echo "❌ Error: Please run this script from the Pure VPN root directory"
    echo "📁 Expected directory structure:"
    echo "   Pure VPN/"
    echo "   ├── frontend/"
    echo "   ├── backend/"
    echo "   └── deploy-vercel.sh"
    exit 1
fi

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    echo "📦 Installing Vercel CLI..."
    npm install -g vercel
fi

# Get VPS IP from user
read -p "🌐 Enter your VPS IP address (e.g., 95.179.152.203): " VPS_IP

if [ -z "$VPS_IP" ]; then
    echo "❌ VPS IP is required!"
    exit 1
fi

# Validate IP format (basic check)
if [[ ! $VPS_IP =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "❌ Invalid IP format! Please enter a valid IP address"
    exit 1
fi

API_URL="http://${VPS_IP}:8000"

echo "✅ Using API URL: $API_URL"

# Navigate to frontend directory
cd frontend

# Create .env.local for deployment
echo "📝 Creating environment configuration..."
cat > .env.local << EOF
# Pure VPN - Vercel Deployment Configuration
NEXT_PUBLIC_API_URL=$API_URL
EOF

echo "✅ Environment configured with API URL: $API_URL"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    npm install
fi

# Build the project locally to test
echo "🔨 Building project locally..."
npm run build

# Deploy to Vercel
echo "🚀 Deploying to Vercel..."
echo ""
echo "📋 During deployment, Vercel will ask you to:"
echo "   1. Set up your project (if first time)"
echo "   2. Choose deployment settings"
echo ""
echo "🔧 Important: Set this environment variable in Vercel dashboard:"
echo "   NEXT_PUBLIC_API_URL = $API_URL"
echo ""

# Deploy with environment variable
vercel --env NEXT_PUBLIC_API_URL="$API_URL"

echo ""
echo "🎉 Deployment initiated!"
echo ""
echo "🔧 Next steps:"
echo "1. 📊 Check Vercel dashboard for deployment status"
echo "2. 🌐 Ensure your VPS firewall allows port 8000:"
echo "   sudo ufw allow 8000"
echo "3. 🔒 Update backend CORS if needed"
echo "4. 🧪 Test your deployed app!"
echo ""
echo "📱 Your Pure VPN will be available at:"
echo "   https://your-project-name.vercel.app"
echo ""
echo "🎯 API calls will connect to: $API_URL" 