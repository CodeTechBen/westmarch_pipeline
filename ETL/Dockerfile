FROM public.ecr.aws/lambda/python:3.12

# Basic tools + libs commonly needed by headless Chrome
RUN dnf install -y \
    unzip \
    wget \
    curl \
    tar \
    gzip \
    gcc \
    postgresql-devel \
    atk \
    cups-libs \
    gtk3 \
    libXcomposite \
    libXcursor \
    libXdamage \
    libXext \
    libXi \
    libXrandr \
    libXScrnSaver \
    libXtst \
    pango \
    alsa-lib \
    libXfixes \
    nss \
    nspr \
    mesa-libgbm \
    xorg-x11-fonts-Type1 \
    xorg-x11-fonts-misc \
    && dnf clean all

# Copy requirements first for caching
COPY requirements.txt ${LAMBDA_TASK_ROOT}/requirements.txt
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt

# Copy browser assets into fixed paths expected by Selenium
# Folder names here should match what you unzip/download locally before build:
#   chrome-linux64/
#   chromedriver-linux64/
COPY chrome-linux64 /opt/chrome/
COPY chromedriver-linux64/chromedriver /opt/chromedriver

RUN chmod +x /opt/chromedriver \
    && chmod +x /opt/chrome/chrome

# Copy application code
COPY . ${LAMBDA_TASK_ROOT}

# Lambda handler
CMD ["load_character.lambda_handler"]