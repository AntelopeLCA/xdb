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

