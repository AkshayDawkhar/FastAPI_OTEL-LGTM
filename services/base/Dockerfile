FROM python:3.13-slim
# Set work directory
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates
# Download the latest installer
ADD https://astral.sh/uv/install.sh /uv-installer.sh

# Run the installer then remove it
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

# Copy the rest of the code
COPY ../.. .

RUN uv sync --frozen --no-dev

# Expose FastAPI port
EXPOSE 8000

# Run the app
CMD ["uv", "run", "uvicorn", "main:app","--port", "8000","--host","0.0.0.0"]

# Metadata:
LABEL maintainer="Akshay"
LABEL version="1.0.0"
LABEL description="Fastapi setup with Nginx,PostgreSQL,OTEL."

