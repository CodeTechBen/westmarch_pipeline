FROM public.ecr.aws/lambda/python:3.12

# System deps for psycopg2
RUN dnf install -y gcc postgresql-devel && dnf clean all

# Copy requirements first for better layer caching
COPY requirements.txt ${LAMBDA_TASK_ROOT}/requirements.txt

RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy application code
COPY . ${LAMBDA_TASK_ROOT}

# Lambda handler
CMD ["load_character.lambda_handler"]