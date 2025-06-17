#!/bin/bash

echo "🔧 GitHub Repository Setup Wizard"

read -p "Enter your GitHub username: " GITHUB_USER
read -p "Enter your repository name (e.g., slicer-stl-export): " REPO_NAME
read -p "Choose authentication method (token/ssh): " AUTH_METHOD

cd "$(dirname "$0")"

# Initialize git if needed
if [ ! -d ".git" ]; then
  echo "📁 Initializing git repository..."
  git init
fi

# Create basic .gitignore if not present
if [ ! -f ".gitignore" ]; then
  echo "*.pyc
__pycache__/
*.vtk
*.stl
.vscode
.slicer
.DS_Store" > .gitignore
  git add .gitignore
fi

# Add and commit all files
git add *.py *.slicer README.md .gitignore
git commit -m "Initial commit: added STL export pipeline"

if [ "$AUTH_METHOD" == "token" ]; then
  echo "🌐 Setting up HTTPS with personal access token..."
  REMOTE_URL="https://github.com/$GITHUB_USER/$REPO_NAME.git"
  git remote add origin "$REMOTE_URL"
  git config --global credential.helper store
  echo "📌 Now run: git push -u origin main"
  echo "🔑 Use your personal access token as the password when prompted."
elif [ "$AUTH_METHOD" == "ssh" ]; then
  echo "🔐 Setting up SSH authentication..."
  SSH_REMOTE="git@github.com:$GITHUB_USER/$REPO_NAME.git"
  git remote add origin "$SSH_REMOTE"
  git branch -M main
  git push -u origin main
else
  echo "❌ Unknown authentication method. Please use 'token' or 'ssh'."
  exit 1
fi

echo "✅ GitHub setup complete."
