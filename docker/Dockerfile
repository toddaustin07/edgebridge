FROM python:3
WORKDIR /usr/src/app
COPY ./requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY ./edgebridge.py .
COPY ./edgebridge.cfg /usr/src/app/
CMD [ "python", "./edgebridge.py" ]
