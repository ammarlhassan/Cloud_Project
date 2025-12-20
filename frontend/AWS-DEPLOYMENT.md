# AWS EC2 Deployment Guide

## Quick Deployment Options

### **Option 1: Manual Deployment (Recommended for Learning)** ✅

#### Step 1: Prepare Your EC2 Instance
```bash
# SSH into your EC2
ssh -i your-key.pem ec2-user@your-ec2-ip

# Install Node.js 18
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo yum install -y nodejs

# Verify installation
node --version  # Should be v18.x or higher
npm --version
```

#### Step 2: Upload Frontend from Local
```bash
# On your local machine
cd /home/abdallah/Coding/cloud_project/Cloud_Project/frontend

# Build for production
npm run build

# Create deployment package
tar -czf frontend.tar.gz .next/ public/ node_modules/ package.json package-lock.json next.config.js

# Upload to EC2
scp -i your-key.pem frontend.tar.gz ec2-user@your-ec2-ip:/home/ec2-user/
```

#### Step 3: Setup on EC2
```bash
# SSH into EC2
ssh -i your-key.pem ec2-user@your-ec2-ip

# Create directory
mkdir -p ~/cloud-learning-frontend
cd ~/cloud-learning-frontend

# Extract files
tar -xzf ../frontend.tar.gz

# Create production environment file
cat > .env.local << 'EOF'
NEXT_PUBLIC_API_GATEWAY_URL=http://localhost:5000
NODE_ENV=production
EOF

# Install PM2 for process management
sudo npm install -g pm2

# Start the application
pm2 start npm --name "frontend" -- start

# Save PM2 configuration (auto-restart on reboot)
pm2 save
pm2 startup
# Run the command it outputs (starts PM2 on boot)
```

#### Step 4: Configure Security Group
In AWS Console → EC2 → Security Groups:
- Add Inbound Rule: **Port 3000**, TCP, Source: 0.0.0.0/0
- Keep Port 5000 open (API Gateway)

#### Step 5: Access Your App
```
http://your-ec2-public-ip:3000
```

---

### **Option 2: Automated Script** 🚀

Use the deployment script:

```bash
# 1. Edit the script with your EC2 details
nano deploy-frontend-ec2.sh

# Update these lines:
EC2_IP="54.XXX.XXX.XXX"  # Your EC2 public IP
KEY_FILE="path/to/your-key.pem"

# 2. Make executable
chmod +x deploy-frontend-ec2.sh

# 3. Run deployment
./deploy-frontend-ec2.sh
```

---

### **Option 3: Docker with Docker Compose** 🐳

Add frontend to your existing docker-compose.learner-lab.yml:

```yaml
# Add this service to your docker-compose.learner-lab.yml

  frontend:
    build:
      context: .
      dockerfile: docker/dockerfiles/Dockerfile.frontend
    image: ${ECR_REGISTRY:-localhost}/frontend:${FRONTEND_VERSION:-1.0.0}
    container_name: frontend
    hostname: frontend
    ports:
      - "3000:3000"
    networks:
      - learner-lab-network
    environment:
      NEXT_PUBLIC_API_GATEWAY_URL: "http://api-gateway:5000"
      NODE_ENV: "production"
    depends_on:
      - api-gateway
```

Then deploy:
```bash
# On EC2
docker-compose -f docker-compose.learner-lab.yml up -d frontend
```

---

## Environment Variables Configuration

### **For Same EC2 Deployment:**
```env
# .env.local (frontend communicates with API Gateway on same machine)
NEXT_PUBLIC_API_GATEWAY_URL=http://localhost:5000
```

### **For Separate EC2 or Public Access:**
```env
# .env.local (use EC2 public IP or domain)
NEXT_PUBLIC_API_GATEWAY_URL=http://54.XXX.XXX.XXX:5000
```

⚠️ **Important:** If you want users to access from outside, API Gateway must be accessible from internet (Security Group port 5000 open)

---

## Production Best Practices

### 1. Use Nginx as Reverse Proxy (Optional but Recommended)

```bash
# Install nginx
sudo yum install -y nginx

# Configure nginx
sudo nano /etc/nginx/conf.d/cloud-learning.conf
```

Add this configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;  # Or use IP

    # Frontend
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # API Gateway
    location /api/ {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

```bash
# Start nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Update .env.local for frontend
cat > .env.local << 'EOF'
NEXT_PUBLIC_API_GATEWAY_URL=http://localhost
EOF

# Restart frontend
pm2 restart frontend
```

Now access via: `http://your-ec2-ip` (port 80)

### 2. Use Domain Name (Optional)

1. Register domain or use Route 53
2. Point A record to EC2 public IP
3. Update nginx server_name
4. Add SSL with Let's Encrypt:
```bash
sudo yum install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## Useful PM2 Commands

```bash
# View logs
pm2 logs frontend

# Real-time monitoring
pm2 monit

# Restart app
pm2 restart frontend

# Stop app
pm2 stop frontend

# View all processes
pm2 status

# View detailed info
pm2 show frontend
```

---

## Troubleshooting

### Frontend can't connect to backend:
```bash
# Test API Gateway from EC2
curl http://localhost:5000/health

# Check if port 5000 is listening
sudo netstat -tulpn | grep 5000

# Check docker containers
docker ps | grep api-gateway
```

### Port 3000 already in use:
```bash
# Find process using port 3000
sudo lsof -i :3000

# Kill it
sudo kill -9 <PID>

# Or use different port in PM2
pm2 start npm --name "frontend" -- start -- -p 3001
```

### Build fails:
```bash
# Clear Next.js cache
rm -rf .next
npm run build
```

---

## Security Checklist

- [ ] Update AWS credentials regularly (they expire)
- [ ] Use IAM roles instead of access keys (recommended)
- [ ] Enable HTTPS with SSL certificate
- [ ] Restrict Security Group rules (don't use 0.0.0.0/0 in production)
- [ ] Use environment variables (never commit .env files)
- [ ] Enable CloudWatch logging
- [ ] Set up auto-scaling (optional)
- [ ] Regular backups of RDS

---

## Cost Optimization

1. **Use same EC2 for frontend + backend** (saves money)
2. **Stop EC2 when not in use** (AWS Learner Lab)
3. **Use t2.medium or larger** for running all services
4. **Monitor S3 storage costs** (delete old files)

---

## Next Steps After Deployment

1. Test all features (chat, document upload, quiz, etc.)
2. Check browser console for errors
3. Monitor PM2 logs for issues
4. Set up CloudWatch for monitoring
5. Create backup/restore procedures
6. Document your deployment process
