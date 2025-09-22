#!/bin/bash
echo "🏗️ Building React Frontend..."

# Install Node.js dependencies
cd frontend
npm install

# Build React app
npm run build

echo "✅ Frontend build complete!"

# Go back to root
cd ..

echo "🚀 Ready for Railway deployment!"
