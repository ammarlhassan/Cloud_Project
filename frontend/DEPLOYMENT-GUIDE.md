# Frontend Deployment Guide

## ✅ **What I've Done**

I've updated your Next.js frontend to **perfectly match your actual backend implementation**:

### **1. API Endpoints Match Your Backend**

Your API Gateway uses `/api/v1/` prefix for all endpoints. The frontend now connects to:

```
Authentication:
- POST /api/v1/auth/login
- POST /api/v1/auth/refresh  
- GET /api/v1/auth/verify

Documents (S3 Integration):
- POST /api/v1/documents/upload
- GET /api/v1/documents
- GET /api/v1/documents/{id}
- DELETE /api/v1/documents/{id}
- GET /api/v1/documents/{id}/download
- GET /api/v1/documents/{id}/notes

Chat:
- POST /api/v1/chat/sessions
- POST /api/v1/chat/sessions/{id}/messages
- GET /api/v1/chat/sessions/{id}/messages

Quiz:
- POST /api/v1/quizzes/generate
- GET /api/v1/quizzes/{id}
- POST /api/v1/quizzes/{id}/submit

STT:
- POST /api/v1/stt/transcribe
- GET /api/v1/stt/status/{taskId}

TTS:
- POST /api/v1/tts/synthesize
- GET /api/v1/tts/voices
```

### **2. Port Configuration**

- Your API Gateway runs on **port 5000** (from docker-compose)
- Frontend default: `http://localhost:5000`

### **3. Authentication**

- JWT token automatically added to all requests
- Token stored in localStorage
- Protected routes redirect to login
- Navbar shows user info when logged in

### **4. AWS S3 Integration**

- "My Documents" page shows files from S3 buckets:
  - `document-reader-storage-dev-334413050048`
  - `tts-service-storage-dev-334413050048`
  - `stt-service-storage-dev-334413050048`
  - `chat-service-storage-dev-334413050048`
  - `quiz-service-storage-dev-334413050048`

## 🚀 **How to Run**

### **Option 1: Local Development (Frontend Only)**

```bash
cd frontend
npm install
npm run dev
```

Visit: http://localhost:3000

Make sure your backend services are running via docker-compose!

### **Option 2: Connect to AWS Backend**

1. Start your services on AWS (you already have them running)

2. Update `.env.local` with your EC2 public IP:

```bash
# Get your EC2 instance public IP
# Then update .env.local:
NEXT_PUBLIC_API_GATEWAY_URL=http://YOUR_EC2_PUBLIC_IP:5000
```

3. Make sure your EC2 Security Group allows:
   - Port 5000 (API Gateway)
   - Port 3000 (Frontend - if running on EC2)

### **Option 3: Deploy Frontend to AWS**

#### **A. Deploy on Same EC2 (Easiest)**

```bash
# On your EC2 instance
cd /home/ec2-user/Cloud_Project/frontend
npm install
npm run build
npm start  # Runs on port 3000
```

Access at: `http://YOUR_EC2_IP:3000`

#### **B. Deploy to S3 + CloudFront (Production)**

```bash
# Build static files
npm run build
npm run export  # If using static export

# Upload to S3
aws s3 sync out/ s3://your-frontend-bucket/ --delete

# Set up CloudFront distribution pointing to S3
```

## 🔧 **Environment Variables**

Update `frontend/.env.local`:

```env
# Local development
NEXT_PUBLIC_API_GATEWAY_URL=http://localhost:5000

# AWS EC2 deployment
NEXT_PUBLIC_API_GATEWAY_URL=http://54.XXX.XXX.XXX:5000

# With Load Balancer
NEXT_PUBLIC_API_GATEWAY_URL=http://your-alb-xxxxx.us-east-1.elb.amazonaws.com

# Production with domain
NEXT_PUBLIC_API_GATEWAY_URL=https://api.yourdomain.com
```

## 🔐 **Testing Authentication**

Your API Gateway currently has a simplified auth endpoint. To test:

```bash
# Login (accepts any email/password for now)
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "test123"}'

# You'll get back:
{
  "token": "eyJ0eXAiOiJKV1QiLC...",
  "user": {
    "id": "user_1234",
    "email": "test@example.com"
  }
}
```

The frontend will:
1. Store the token in localStorage
2. Add `Authorization: Bearer <token>` to all API requests
3. Redirect to `/dashboard` after login

## 📦 **Docker Deployment (Recommended)**

Add frontend to your `docker-compose.learner-lab.yml`:

```yaml
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    image: ${ECR_REGISTRY:-localhost}/frontend:${FRONTEND_VERSION:-1.0.0}
    container_name: frontend
    hostname: frontend
    ports:
      - "3000:3000"
    networks:
      - learner-lab-network
    environment:
      NEXT_PUBLIC_API_GATEWAY_URL: http://api-gateway:5000
    depends_on:
      - api-gateway
```

Then:

```bash
docker-compose -f docker-compose.learner-lab.yml up -d frontend
```

## 📡 **CORS Configuration**

Your backend services already have CORS enabled via `flask_cors`. If you get CORS errors:

1. Check API Gateway CORS is enabled
2. Ensure proper headers in responses
3. Verify your frontend URL is allowed

## 🎯 **Next Steps**

1. **Test Locally:**
   ```bash
   # Terminal 1: Start backend (you already have this)
   cd Cloud_Project
   docker-compose -f docker-compose.learner-lab.yml up
   
   # Terminal 2: Start frontend
   cd Cloud_Project/frontend
   npm run dev
   ```

2. **Deploy to AWS:**
   - Push frontend to EC2
   - Update .env.local with EC2 IP
   - Configure security groups
   - Set up nginx as reverse proxy (optional)

3. **Production Setup:**
   - Add proper user registration endpoint in API Gateway
   - Set up PostgreSQL user management database
   - Configure rate limiting
   - Add SSL/TLS certificates
   - Set up CloudFront for frontend

## 🐛 **Troubleshooting**

### **Can't connect to backend:**
```bash
# Check API Gateway is running
curl http://localhost:5000/health

# Check from frontend container
curl http://api-gateway:5000/health
```

### **Authentication not working:**
- Check browser console for token
- Verify Authorization header is being sent
- Check API Gateway logs

### **File upload failing:**
- Check S3 bucket permissions
- Verify AWS credentials in docker-compose
- Check file size limits

## 📝 **Key Features Implemented**

✅ JWT Authentication  
✅ Protected Routes  
✅ User Dashboard  
✅ Document Upload to S3  
✅ "My Documents" page with S3 files  
✅ Chat Interface  
✅ Quiz Generator  
✅ Speech-to-Text  
✅ Text-to-Speech  
✅ Responsive Mobile Design  
✅ Error Handling  
✅ Loading States  

Your frontend is **100% ready** and matches your backend API structure! 🎉
