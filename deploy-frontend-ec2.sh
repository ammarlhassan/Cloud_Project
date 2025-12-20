#!/bin/bash

echo "🚀 AWS EC2 Deployment Script for Cloud Learning Platform"
echo "=========================================================="
echo ""

# Configuration
EC2_IP="YOUR_EC2_PUBLIC_IP"
KEY_FILE="your-key.pem"
EC2_USER="ec2-user"

echo "📋 Deployment Checklist:"
echo "  1. ✅ Backend services running on EC2 (docker-compose)"
echo "  2. ✅ Port 5000 open (API Gateway)"
echo "  3. ⚠️  Update EC2_IP and KEY_FILE in this script"
echo ""

# Check if configuration is updated
if [ "$EC2_IP" == "YOUR_EC2_PUBLIC_IP" ]; then
    echo "❌ ERROR: Please update EC2_IP in this script first!"
    echo "   Edit this file and set your EC2 public IP address"
    exit 1
fi

if [ ! -f "$KEY_FILE" ]; then
    echo "❌ ERROR: Key file '$KEY_FILE' not found!"
    echo "   Please update KEY_FILE in this script"
    exit 1
fi

echo "🔨 Building frontend..."
cd frontend
npm run build

if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi

echo "✅ Build complete!"
echo ""

echo "📦 Creating deployment package..."
tar -czf ../frontend-deploy.tar.gz \
    .next/ \
    public/ \
    node_modules/ \
    package.json \
    package-lock.json \
    next.config.js

cd ..

echo "📤 Uploading to EC2..."
scp -i "$KEY_FILE" frontend-deploy.tar.gz "$EC2_USER@$EC2_IP:/tmp/"

if [ $? -ne 0 ]; then
    echo "❌ Upload failed!"
    exit 1
fi

echo "🔧 Setting up on EC2..."
ssh -i "$KEY_FILE" "$EC2_USER@$EC2_IP" << 'ENDSSH'
    # Install Node.js if not installed
    if ! command -v node &> /dev/null; then
        echo "📥 Installing Node.js..."
        curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
        sudo yum install -y nodejs
    fi
    
    # Install PM2 if not installed
    if ! command -v pm2 &> /dev/null; then
        echo "📥 Installing PM2..."
        sudo npm install -g pm2
    fi
    
    # Create app directory
    mkdir -p /home/ec2-user/cloud-learning-frontend
    cd /home/ec2-user/cloud-learning-frontend
    
    # Extract deployment package
    echo "📦 Extracting files..."
    tar -xzf /tmp/frontend-deploy.tar.gz
    rm /tmp/frontend-deploy.tar.gz
    
    # Create production .env.local
    echo "⚙️  Configuring environment..."
    cat > .env.local << EOF
NEXT_PUBLIC_API_GATEWAY_URL=http://localhost:5000
NODE_ENV=production
EOF
    
    # Stop existing PM2 process if running
    pm2 stop frontend 2>/dev/null || true
    pm2 delete frontend 2>/dev/null || true
    
    # Start with PM2
    echo "🚀 Starting frontend..."
    pm2 start npm --name "frontend" -- start
    pm2 save
    
    echo "✅ Deployment complete!"
    echo ""
    echo "📊 PM2 Status:"
    pm2 status
ENDSSH

echo ""
echo "✅ Deployment successful!"
echo ""
echo "🌐 Access your application:"
echo "   http://$EC2_IP:3000"
echo ""
echo "📝 Useful commands:"
echo "   ssh -i $KEY_FILE $EC2_USER@$EC2_IP"
echo "   pm2 logs frontend    # View logs"
echo "   pm2 restart frontend # Restart app"
echo "   pm2 status           # Check status"
echo ""
echo "⚠️  Security Group Requirements:"
echo "   - Port 3000: Frontend (0.0.0.0/0)"
echo "   - Port 5000: API Gateway (0.0.0.0/0)"
