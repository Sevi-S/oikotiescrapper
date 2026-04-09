FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir requests beautifulsoup4 geopy tabulate
COPY oikotie_metro.py viewer.py ./
VOLUME /app/data
ENV RESULTS_DIR=/app/data
EXPOSE 8080
CMD ["python3", "viewer.py"]
