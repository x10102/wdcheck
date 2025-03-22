FROM python:3.13.2-alpine

WORKDIR /app

RUN apk add --no-cache libxml2 libxslt

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "./main.py"]