FROM mcr.microsoft.com/playwright:v1.23.1-focal
RUN apt-get update && apt-get install -y \
  python3-pip
RUN pip install --upgrade pip 
RUN pip install playwright && playwright install
RUN pip install pytest-playwright
