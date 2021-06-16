FROM python:3

WORKDIR /app
ADD speedtest .

RUN pip3 install -r requirements.txt

CMD ["python", "main.py"]
