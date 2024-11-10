FROM python:3.12-slim AS build
RUN python3 -m venv /opt/build-tools
RUN /opt/build-tools/bin/pip install -U pip
RUN /opt/build-tools/bin/pip install pip-tools build

COPY . /usr/src/juudge
WORKDIR /usr/src/juudge
RUN /opt/build-tools/bin/pip-compile \
    --quiet \
    --generate-hashes \
    --strip-extras \
    --output-file /requirements.txt

RUN python3 -m venv /opt/juudge
RUN /opt/juudge/bin/pip install -U pip
RUN /opt/juudge/bin/pip install --no-deps --requirement /requirements.txt
RUN /opt/juudge/bin/pip install --no-deps /usr/src/juudge


FROM python:3.12-slim AS prod
COPY ./docker-resources/main.bash /opt/juudge/bin/juudge-main.bash
COPY ./docker-resources/logging.yaml /opt/juudge/etc/logging.yaml
RUN chmod +x /opt/juudge/bin/juudge-main.bash
COPY --from=build /opt/juudge /opt/juudge
COPY --from=build /requirements.txt /opt/juudge/requirements.txt
RUN  mkdir /opt/juudge/logs
WORKDIR /
EXPOSE 8000
ENTRYPOINT ["/opt/juudge/bin/juudge-main.bash"]
