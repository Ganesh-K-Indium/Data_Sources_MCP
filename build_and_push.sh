#!/bin/bash

# Build and Push Docker Image to ECR
# Usage: ./build_and_push.sh [aws-region] [repository-name] [tag]

set -e

# Default values
AWS_REGION=${1:-us-east-1}
REPO_NAME=${2:-data-sources-mcp}
TAG=${3:-latest}

# AWS Account ID
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# ECR Repository URI
ECR_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPO_NAME}"

echo "Building Docker image..."
docker build -t ${REPO_NAME}:${TAG} .

echo "Authenticating with ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

echo "Creating ECR repository if it doesn't exist..."
aws ecr describe-repositories --repository-names ${REPO_NAME} --region ${AWS_REGION} || \
aws ecr create-repository --repository-name ${REPO_NAME} --region ${AWS_REGION}

echo "Tagging image..."
docker tag ${REPO_NAME}:${TAG} ${ECR_URI}:${TAG}

echo "Pushing image to ECR..."
docker push ${ECR_URI}:${TAG}

echo "✅ Successfully pushed ${ECR_URI}:${TAG}"
echo ""
echo "To run the container:"
echo "docker run -p 8000-8006:8000-8006 -e GROQ_API_KEY=your_key -e OPENAI_API_KEY=your_key -e CONFLUENCE_URL=your_url -e JIRA_URL=your_url ${ECR_URI}:${TAG}"
echo ""
echo "API endpoints:"
echo "- REST API: http://localhost:8006/chat (POST with JSON body {\"message\": \"your query\"})"
echo "- API Docs: http://localhost:8006/docs"