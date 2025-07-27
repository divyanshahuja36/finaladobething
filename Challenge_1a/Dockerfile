FROM python:3.10-slim

# Install system dependencies for PyMuPDF
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the main script
COPY process_pdfs.py .

# Create directories for data
RUN mkdir -p sample_dataset/pdfs sample_dataset/outputs schema


# Run the extraction script
CMD ["python", "process_pdfs.py"]