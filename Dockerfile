FROM python:3.12-slim
WORKDIR /cutbook
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . ./
CMD ["waitress-serve", "--listen=0.0.0.0:8080", "--call", "app.main:create_app"]
