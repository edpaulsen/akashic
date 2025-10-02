# AWS Lambda Python base image
FROM public.ecr.aws/lambda/python:3.11

# Copy app
COPY app /var/task/app
COPY requirements.txt /var/task/requirements.txt

# Install deps
RUN python -m pip install --upgrade pip && pip install -r /var/task/requirements.txt

# Handler is app.aws_handler:handler
CMD [ "app.aws_handler.handler" ]
