FROM tiangolo/uvicorn-gunicorn-fastapi:python3.10
WORKDIR /usr/src/xdb/
COPY requirements.txt /usr/src/xdb/requirements.txt
#RUN pip install --force-reinstall httpcore==0.15
RUN pip install --upgrade -r /usr/src/xdb/requirements.txt
#RUN pip install synonym_dict
COPY . /usr/src/xdb/

#RUN apt install -y unzip
#RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
#RUN unzip awscliv2.zip
#RUN ./aws/install

CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "80", "--reload"]
