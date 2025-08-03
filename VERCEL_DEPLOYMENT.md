# 🚀 Pure VPN - Vercel Deployment Guide

Deploy your Pure VPN frontend to Vercel for global CDN distribution while keeping your backend secure on your VPS.

## 🎯 Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Vercel CDN    │    │   Your VPS      │    │  WireGuard VPN  │
│  (Frontend UI)  │◄──►│  (Backend API)  │◄──►│     Server      │
│ Global Delivery │    │ Pure VPN Logic  │    │  (Your Server)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
     Worldwide              Your Control           Your Privacy
```

## ✨ Benefits

- **🌍 Global CDN**: Lightning fast loading worldwide
- **🔒 Secure Backend**: Keep your VPN logic on your controlled VPS
- **💰 Cost Effective**: Free Vercel hosting + ~$6/month VPS
- **📱 Mobile Optimized**: Perfect mobile experience via CDN
- **🚀 Auto Deployments**: Deploy via Git commits

---

## 📋 Prerequisites

1. **VPS with Pure VPN Backend Running**:
   - Backend accessible at `http://YOUR-VPS-IP:8000`
   - Port 8000 open in firewall
   - CORS properly configured

2. **Development Environment**:
   - Node.js 18+ installed
   - Git repository set up
   - Vercel account (free at [vercel.com](https://vercel.com))

---

## 🚀 Quick Deployment (5 minutes)

### Method 1: Automated Script

```bash
# From your Pure VPN root directory
chmod +x deploy-vercel.sh
./deploy-vercel.sh
```

### Method 2: Manual Deployment

#### Step 1: Install Vercel CLI

```bash
npm install -g vercel
```

#### Step 2: Configure Environment

```bash
cd frontend

# Create environment file
cat > .env.local << EOF
NEXT_PUBLIC_API_URL=http://YOUR-VPS-IP:8000
EOF

# Example:
# NEXT_PUBLIC_API_URL=http://95.179.152.203:8000
```

#### Step 3: Build and Test Locally

```bash
npm install
npm run build
npm start

# Test at http://localhost:3000
# Verify it connects to your VPS backend
```

#### Step 4: Deploy to Vercel

```bash
vercel

# Follow the prompts:
# 1. Link to existing project or create new
# 2. Choose settings (defaults are usually fine)
# 3. Deploy!
```

---

## 🔧 VPS Backend Setup

Ensure your VPS backend is properly configured for external access:

### 1. Check Backend is Running

```bash
# SSH to your VPS
ssh root@YOUR-VPS-IP

# Check Pure VPN backend
curl http://localhost:8000/health

# Should return: {"status": "healthy", "message": "Pure VPN API is running"}
```

### 2. Open Firewall Port

```bash
# Allow external access to port 8000
sudo ufw allow 8000
sudo ufw status

# Verify port is accessible externally
curl http://YOUR-VPS-IP:8000/health
```

### 3. Update CORS Configuration

The backend should already be configured for Vercel, but verify:

```python
# In backend/main.py, should include:
allowed_origins = [
    # ... other origins ...
    "https://*.vercel.app",
    "https://vercel.app",
]

# And regex pattern:
cors_regex_patterns.append(r"https://.*\.vercel\.app")
```

---

## 🌐 Vercel Dashboard Configuration

### Environment Variables

In your Vercel project dashboard, add:

| Variable | Value | Example |
|----------|-------|---------|
| `NEXT_PUBLIC_API_URL` | `http://YOUR-VPS-IP:8000` | `http://95.179.152.203:8000` |

### Domain Configuration

1. **Custom Domain** (Optional):
   - Add your domain in Vercel dashboard
   - Point DNS to Vercel
   - Automatic HTTPS included

2. **Default Domain**:
   - `https://your-project-name.vercel.app`
   - Automatically assigned

---

## 🧪 Testing Your Deployment

### 1. Frontend Tests

```bash
# Test Vercel deployment
curl -I https://your-project-name.vercel.app
# Should return 200 OK

# Test API connection (from browser console)
fetch('https://your-project-name.vercel.app')
.then(() => console.log('Frontend loads'))

# Check API calls (in browser console)
fetch(process.env.NEXT_PUBLIC_API_URL + '/health')
.then(r => r.json())
.then(console.log)
```

### 2. Full Integration Test

1. **Open your Vercel URL**: `https://your-project-name.vercel.app`
2. **Enter username**: Any name you like
3. **Click "Connect to Pure VPN"**
4. **Verify**: Configuration should generate successfully
5. **Test VPN**: Connect using the generated config

---

## 🔄 Automatic Deployments

### GitHub Integration

1. **Connect Repository**:
   - Link your GitHub repo to Vercel
   - Every push to `main` automatically deploys

2. **Branch Deployments**:
   - Each branch gets a preview URL
   - Perfect for testing changes

### Manual Deployments

```bash
# From frontend directory
vercel --prod  # Deploy to production
vercel         # Deploy preview
```

---

## 🎯 Production Optimization

### Performance

```javascript
// next.config.js optimizations included:
{
  "headers": [
    {
      "key": "X-DNS-Prefetch-Control",
      "value": "on"
    }
  ]
}
```

### Security Headers

Automatic security headers via `vercel.json`:
- `X-Frame-Options: DENY`
- `X-Content-Type-Options: nosniff`
- `Referrer-Policy: strict-origin-when-cross-origin`

### Monitoring

- **Vercel Analytics**: Built-in performance monitoring
- **Error Tracking**: Automatic error reporting
- **Real User Monitoring**: See actual user performance

---

## 🔒 Security Considerations

### Environment Variables

```bash
# ✅ Correct - Public API URL (read-only access)
NEXT_PUBLIC_API_URL=http://your-vps-ip:8000

# ❌ Wrong - Never put sensitive data in NEXT_PUBLIC_*
NEXT_PUBLIC_SECRET_KEY=sensitive_data
```

### Backend Security

```python
# ✅ Proper CORS configuration
allowed_origins = [
    "https://your-domain.vercel.app",  # Specific domain
    # "https://*.vercel.app",          # Or wildcard for testing
]

# ❌ Avoid in production
allow_origins=["*"]  # Too permissive
```

### HTTPS Considerations

- **Vercel Frontend**: Automatic HTTPS
- **VPS Backend**: HTTP is OK for API-only traffic
- **Mixed Content**: Modern browsers allow HTTPS→HTTP API calls

---

## 🆘 Troubleshooting

### Common Issues

#### 1. "Network Error" / "Failed to fetch"

```bash
# Check VPS firewall
sudo ufw status
sudo ufw allow 8000

# Check backend is running
curl http://YOUR-VPS-IP:8000/health

# Check CORS configuration
curl -H "Origin: https://your-app.vercel.app" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: X-Requested-With" \
     -X OPTIONS \
     http://YOUR-VPS-IP:8000/status
```

#### 2. Environment Variables Not Working

```bash
# Verify in Vercel dashboard
vercel env ls

# Check in browser console
console.log(process.env.NEXT_PUBLIC_API_URL)

# Redeploy after env changes
vercel --prod
```

#### 3. Build Failures

```bash
# Test build locally first
cd frontend
npm run build

# Check TypeScript errors
npm run type-check

# Check for missing dependencies
npm install
```

### Debug Tools

```javascript
// Add to frontend for debugging
console.log('API Base URL:', process.env.NEXT_PUBLIC_API_URL)
console.log('Environment:', process.env.NODE_ENV)

// Network tab in browser dev tools
// Check API calls are going to correct URL
```

---

## 📊 Monitoring & Analytics

### Built-in Vercel Analytics

```bash
# Enable in Vercel dashboard
# Provides:
# - Page load times
# - Core Web Vitals
# - User geography
# - Device types
```

### Custom Monitoring

```javascript
// Add to pages/_app.tsx for custom tracking
export default function MyApp({ Component, pageProps }) {
  useEffect(() => {
    // Track API response times
    // Log user interactions
    // Monitor VPN connection success rates
  }, [])
  
  return <Component {...pageProps} />
}
```

---

## 🚀 Advanced Deployments

### Multi-Environment Setup

```bash
# Production
vercel --prod

# Staging
vercel --target staging

# Development preview
vercel
```

### Custom Domains

```bash
# Add domain via CLI
vercel domains add yourdomain.com

# Or via dashboard
# 1. Go to project settings
# 2. Add domain
# 3. Configure DNS
```

### Team Collaboration

```bash
# Invite team members
vercel teams invite member@example.com

# Manage access
vercel teams list
```

---

## 🎉 Success Checklist

- [ ] ✅ Vercel deployment successful
- [ ] 🌐 Custom domain configured (optional)
- [ ] 🔧 Environment variables set
- [ ] 🔥 VPS firewall configured
- [ ] 🧪 Full end-to-end test completed
- [ ] 📊 Analytics enabled
- [ ] 🔄 Auto-deployment configured
- [ ] 📱 Mobile testing completed

---

## 💡 Pro Tips

### 1. **Cost Optimization**
```bash
# Free tier limits:
# - 100GB bandwidth/month
# - 100 deployments/day
# - Unlimited static requests
```

### 2. **Performance Optimization**
```bash
# Use Vercel Edge Network
# Automatic image optimization
# Built-in CDN
# Zero-config performance
```

### 3. **Development Workflow**
```bash
# Local development with VPS backend
cd frontend
NEXT_PUBLIC_API_URL=http://your-vps-ip:8000 npm run dev

# Preview deployments for testing
git push origin feature-branch
# Automatic preview URL generated
```

---

## 🎯 Final Result

You now have:
- **🌍 Global Frontend**: Fast loading worldwide via Vercel CDN
- **🔒 Secure Backend**: Your VPN logic safe on your VPS
- **📱 Mobile Perfect**: Excellent mobile experience
- **💰 Cost Effective**: ~$6/month total cost
- **🚀 Professional**: Enterprise-grade deployment setup

**Access your Pure VPN**: `https://your-project-name.vercel.app`

**Backend API**: `http://YOUR-VPS-IP:8000`

**Perfect for**: Personal use, family sharing, business teams, and anyone wanting a professional VPN solution with complete control. 