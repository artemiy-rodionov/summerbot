FROM python:3.9
RUN mkdir /code
WORKDIR /code
RUN mkdir /code/instance
COPY requirements.txt .
RUN pip install -r requirements.txt
ADD summer_bot /code/summer_bot
ADD run.py /code
ENTRYPOINT ["python3", "run.py"]
