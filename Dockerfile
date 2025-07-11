# Build React app
FROM node:20 AS client-build
WORKDIR /client
COPY client/package*.json ./
RUN npm install
COPY client .
RUN npm run build

# Main Python image
FROM python:3.12-slim

# Set work directory
WORKDIR /app

# Install dependencies & Create the database directory
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi && \
    mkdir -p /app/db

# Copy project files
COPY . .

# Copy built React app from client-build stage
COPY --from=client-build /client/dist /app/client

# Create a user with the same UID and GID as the host user
ARG UID=1000
ARG GID=1000
RUN addgroup --gid $GID appuser && \
    adduser --disabled-password --gecos '' --uid $UID --gid $GID appuser

# Change ownership of /app to the new user
RUN chown -R appuser:appuser /app

# Switch to the new user
USER appuser

# Expose port (default uvicorn port)
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Start the app with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
