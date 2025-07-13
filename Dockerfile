# Base image with Anaconda
FROM continuumio/miniconda3

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DOCKER=true

# Set working directory
WORKDIR /app

# Install system dependencies
# git is needed for some pip installs from git repos
# ffmpeg is a common dependency for audio processing libraries like librosa
# espeak-ng is required for phonemization
RUN apt-get update && apt-get install -y \
    git \
    ffmpeg \
    espeak-ng \
    && apt-get clean

# Copy the application files into the container
COPY . .

# Create a conda environment for the application
# StyleTTS2 requires Python >= 3.9, using 3.11 for consistency
RUN conda create -n styletts2 python=3.11 -y

# Activate the conda environment for subsequent commands
SHELL ["conda", "run", "-n", "styletts2", "/bin/bash", "-c"]

# Install dependencies from requirements.txt
RUN pip install -r requirements.txt

# Install python-crfsuite from conda-forge (fixes MacOS import issues)
RUN conda install -c conda-forge python-crfsuite -y

# Download NLTK data (required by StyleTTS2)
RUN python -c "import nltk; nltk.download('punkt_tab', quiet=True)"

# Pre-download the StyleTTS2 model during build time
# This ensures the model is cached in the Docker image and doesn't need to be downloaded at runtime
# Note: Model files should be available in the StyleTTS2-LibriTTS directory
RUN python -c "import os; print('Checking model files...'); print('Model checkpoint exists:', os.path.exists('StyleTTS2-LibriTTS/Models/LibriTTS/epoch_2nd_00012.pth')); print('Config exists:', os.path.exists('StyleTTS2-LibriTTS/Models/LibriTTS/config_vokan.yml'))"

# Expose the port the server will run on (port 8013 as specified in server.py)
EXPOSE 8013

# Command to run the application server with conda environment activated
CMD ["conda", "run", "-n", "styletts2", "python", "server.py"] 