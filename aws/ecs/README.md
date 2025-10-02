# ECS Fargate — Run Notes (Quick)

1) Build and push your image to ECR (similar steps as Lambda).
2) Create ECS Cluster (Fargate), Task Definition (CPU/Memory like 0.5 vCPU/1GB), container listening on 8000.
3) Create a Service behind an Application Load Balancer (ALB), route HTTP 80 → target group → port 8000.
4) Set desired count = 1, auto scaling optional.

Minimal local test:
```bash
docker build -t akashic-ecs -f aws/ecs/Dockerfile .
docker run --rm -p 8000:8000 akashic-ecs
curl http://127.0.0.1:8000/healthz
```
