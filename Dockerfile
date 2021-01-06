# set base image (host OS)
#  https://www.docker.com/blog/containerized-python-development-part-1/
FROM python:3.8

# Install dependencies:
COPY requirements.txt .
RUN pip install -r requirements.txt

ENV LISTEN_PORT=8000
EXPOSE 8000 
USER root

# Run the application:
COPY main.py .
COPY payload_wrapper.py .
COPY elastic_search_wrapper.py .

CMD ["python", "main.py"]

# docker build -t vaultsearch .

# docker run -d -p 8000:8000 --name search vaultsearch
