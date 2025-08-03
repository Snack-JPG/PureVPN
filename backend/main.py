from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
import os
import json
import asyncio
from datetime import datetime
import qrcode
import io
import base64
from dotenv import load_dotenv

from existing_server_manager import ExistingServerVPNManager

load_dotenv()

app = FastAPI(
    title="Pure VPN", 
    description="Clean, fast, secure VPN with no tracking or logs",
    version="1.0.0"
)

# Enhanced CORS configuration for VPS deployment and Vercel
allowed_origins = [
    # Local development
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3001",
    "http://0.0.0.0:3001",
    
    # Vercel deployment domains
    "https://*.vercel.app",
    "https://vercel.app",
]

# Add production origins from environment
production_origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
for origin in production_origins:
    if origin.strip():
        allowed_origins.append(origin.strip())

# Build CORS regex pattern for flexible domain matching
cors_regex_patterns = []

# Always allow Vercel domains
cors_regex_patterns.append(r"https://.*\.vercel\.app")

# If PRODUCTION mode, also allow VPS IP patterns
if os.getenv("PRODUCTION"):
    cors_regex_patterns.extend([
        r"http://.*:3001",
        r"http://.*:8000",
        r"https://.*:3001",
        r"https://.*:8000"
    ])

# Combine all regex patterns
combined_regex = "|".join(cors_regex_patterns) if cors_regex_patterns else None

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=combined_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Global VPN manager
try:
    vpn_manager = ExistingServerVPNManager()
    server_info = f"✅ Connected to Pure VPN server: {vpn_manager.server_ip}"
    if os.getenv("PRODUCTION"):
        server_info += " (Production Mode)"
    print(server_info)
except Exception as e:
    print(f"❌ Failed to initialize Pure VPN manager: {e}")
    vpn_manager = None

deployment_status = {"status": "idle", "message": "", "progress": 0}

@app.get("/")
async def root():
    return {
        "message": "Pure VPN API", 
        "status": "running", 
        "version": "1.0.0",
        "description": "Clean, fast, secure VPN with no tracking or logs",
        "mode": "production" if os.getenv("PRODUCTION") else "development"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "vpn_manager": "connected" if vpn_manager else "disconnected"
    }

async def join_vpn_background(username: str):
    """Background task to add user to Pure VPN"""
    global deployment_status

    if not vpn_manager:
        deployment_status = {
            "status": "error",
            "message": "Pure VPN manager not configured. Check environment variables.",
            "progress": 0
        }
        return

    try:
        deployment_status = {"status": "starting", "message": f"Adding {username} to Pure VPN...", "progress": 20}
        
        result = await vpn_manager.join_or_create_vpn(username)
        
        deployment_status = {
            "status": "completed",
            "message": f"Successfully connected {username} to Pure VPN",
            "progress": 100,
            "result": result
        }
    except Exception as e:
        deployment_status = {
            "status": "error",
            "message": str(e),
            "progress": 0
        }

@app.post("/join/{username}")
async def join_vpn(username: str, background_tasks: BackgroundTasks):
    """Connect user to Pure VPN"""
    global deployment_status
    
    if not vpn_manager:
        raise HTTPException(status_code=500, detail="Pure VPN manager not configured")
    
    if deployment_status["status"] == "starting":
        raise HTTPException(status_code=409, detail="VPN connection already in progress")
    
    background_tasks.add_task(join_vpn_background, username)
    deployment_status = {"status": "starting", "message": f"Connecting {username} to Pure VPN", "progress": 5}
    
    return {
        "success": True,
        "message": f"Connecting {username} to Pure VPN",
        "status": "starting"
    }

@app.get("/deployment-status")
async def get_deployment_status():
    return deployment_status

@app.get("/status")
async def get_status():
    """Get Pure VPN server status"""
    try:
        if not vpn_manager:
            return {"status": "error", "message": "Pure VPN manager not configured"}
        
        if deployment_status["status"] == "starting":
            return {
                "status": "processing",
                "message": deployment_status["message"],
                "progress": deployment_status["progress"]
            }
        elif deployment_status["status"] == "error":
            return {
                "status": "error",
                "message": deployment_status["message"]
            }
        elif deployment_status["status"] == "completed" and "result" in deployment_status:
            result = deployment_status["result"]
            return {
                "status": "connected",
                "server_ip": result["server_ip"],
                "connection_type": result["status"],
                "estimated_cost": "Fixed monthly cost"
            }
        
        pool_status = await vpn_manager.get_pool_status()
        
        if pool_status["active_servers"] == 0:
            return {"status": "no_servers", "message": "Pure VPN server not available"}
        
        return {
            "status": "server_ready",
            "active_servers": pool_status["active_servers"],
            "total_peers": pool_status["total_peers"],
            "available_slots": pool_status["available_slots"],
            "server_ip": pool_status["server_ip"],
            "estimated_cost": "Fixed monthly cost"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/disconnect/{username}")
async def disconnect_user(username: str):
    """Disconnect user from Pure VPN"""
    global deployment_status
    
    if not vpn_manager:
        raise HTTPException(status_code=500, detail="Pure VPN manager not configured")
    
    try:
        result = await vpn_manager.disconnect_user(username)
        deployment_status = {"status": "idle", "message": "", "progress": 0}
        return {
            "success": True,
            "message": f"User {username} disconnected from Pure VPN successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config/{username}")
async def get_config(username: str):
    """Get WireGuard config for specific user"""
    if not vpn_manager:
        raise HTTPException(status_code=500, detail="Pure VPN manager not configured")
    
    try:
        config = await vpn_manager.get_user_config(username)
        return {
            "username": username,
            "config": config,
            "filename": f"{username}-pure-vpn.conf"
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Config not found for user: {username}")

@app.get("/qr/{username}")
async def get_qr_code(username: str):
    """Get QR code PNG for user config"""
    if not vpn_manager:
        raise HTTPException(status_code=500, detail="Pure VPN manager not configured")
    
    try:
        config = await vpn_manager.get_user_config(username)
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(config)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        return Response(
            content=img_buffer.getvalue(),
            media_type="image/png",
            headers={"Content-Disposition": f"inline; filename={username}-pure-vpn-qr.png"}
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"QR code generation failed for user: {username}")

@app.get("/test-connection")
async def test_connection():
    """Test connection to Pure VPN server"""
    if not vpn_manager:
        raise HTTPException(status_code=500, detail="Pure VPN manager not configured")
    
    try:
        result = await vpn_manager.test_connection()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/server-status")
async def get_detailed_server_status():
    """Get detailed Pure VPN server information"""
    if not vpn_manager:
        raise HTTPException(status_code=500, detail="Pure VPN manager not configured")
    
    try:
        pool_status = await vpn_manager.get_pool_status()
        connection_test = await vpn_manager.test_connection()
        return {
            "pool_status": pool_status,
            "connection_test": connection_test
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Production-ready server configuration
    host = "0.0.0.0" if os.getenv("PRODUCTION") else "127.0.0.1"
    uvicorn.run(app, host=host, port=8000) 