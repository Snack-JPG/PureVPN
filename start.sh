#!/bin/bash

# Pure VPN Development Server Startup Script

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}🚀 Starting Pure VPN Development Servers${NC}"

# Check if .env exists
if [ ! -f "backend/.env" ]; then
    echo -e "${YELLOW}⚠️  Backend .env file not found${NC}"
    echo "Creating example .env file..."
    cat > backend/.env << EOF
# Pure VPN Configuration
EXISTING_SERVER_IP=95.179.152.203
SSH_USERNAME=root
SSH_PASSWORD=your_password_here
WIREGUARD_PORT=51820
EOF
    echo -e "${YELLOW}📝 Please edit backend/.env with your server details${NC}"
fi

# Check if VULTR_API_KEY exists (legacy support)
if grep -q "VULTR_API_KEY" backend/.env 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Found VULTR_API_KEY in .env - this is no longer needed for existing server mode${NC}"
fi

echo -e "${BLUE}🐍 Starting FastAPI backend on port 8000...${NC}"
echo -e "${BLUE}⚛️  Starting Next.js frontend on port 3000...${NC}"

# Kill existing processes on these ports
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 3000/tcp 2>/dev/null || true

# Start backend
cd backend
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend
cd ../frontend
npm run dev &
FRONTEND_PID=$!

# Go back to project root
cd ..

echo -e "${GREEN}✅ Servers started!${NC}"
echo -e "${BLUE}🌐 Frontend: http://localhost:3000${NC}"
echo -e "${BLUE}🔧 Backend API: http://localhost:8000${NC}"
echo -e "${BLUE}📋 To stop both servers: kill $BACKEND_PID $FRONTEND_PID${NC}"
echo -e "${BLUE}💡 Or just press Ctrl+C twice${NC}"

echo
echo -e "${YELLOW}🌍 Want to access from anywhere? Deploy to your VPS!${NC}"
echo -e "${BLUE}📖 See: vps-quick-start.md${NC}"
echo -e "${BLUE}🚀 Run: ./deploy-to-vps.sh (on your VPS)${NC}"
echo

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID 