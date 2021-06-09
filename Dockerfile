FROM python:3 as api
RUN pip install uvicorn fastapi
WORKDIR /project/api

FROM api as test
RUN pip install pytest pytest-mock pytest-pythonpath
# tool for hot reloading tests
WORKDIR /tmp
RUN git clone --branch 4.6 https://github.com/eradman/entr.git
WORKDIR /tmp/entr
RUN ./configure
RUN make test
RUN make install
WORKDIR /project

FROM python:3 as dagster
RUN apt-get update
RUN apt-get install -y unzip curl
RUN pip install dagster dagster-aws dagster-shell dagit
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
RUN unzip awscliv2.zip
RUN ./aws/install
WORKDIR /project/etl