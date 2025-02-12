# Use Ubuntu-based Python image
FROM ubuntu:22.04

# Set working directory
WORKDIR /app

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Install Python and required packages
RUN apt-get update && \
    apt-get install -y \
    python3.10 \
    python3-pip \
    build-essential \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN python3 -m pip install --upgrade pip

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the project files
COPY . .

# Create data directory
RUN mkdir -p data

# Expose Streamlit port
EXPOSE 8508

# Command to run the app
CMD ["python3", "-m", "streamlit", "run", "code/main.py", "--server.port=8508", "--server.address=0.0.0.0"]
