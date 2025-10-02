# Lambda Container — Deploy Notes (Quick)

## Build & Push
Replace `$ACCOUNT_ID`, `$REGION`, `$REPO` first.

```bash
aws ecr create-repository --repository-name $REPO || true

aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

docker build -t $REPO:latest -f aws/lambda/Dockerfile .

docker tag $REPO:latest $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO:latest
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO:latest
```

## Create Lambda
```bash
aws lambda create-function   --function-name akashic-lookup   --package-type Image   --code ImageUri=$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$REPO:latest   --role arn:aws:iam::$ACCOUNT_ID:role/YourLambdaRoleWithBasicExecution   --timeout 30 --memory-size 512
```

## API Gateway (HTTP API, Lambda proxy)
Create an HTTP API and integrate with the Lambda. No special mapping needed (Mangum handles routes).
