# 参考
# https://stackoverflow.com/questions/50333650/install-python-package-in-docker-file

# $ docker build -t shusan_hatsugen_db . --no-root

FROM python:3.10.2
WORKDIR /usr/src/

ARG HOST_UID=1000
ARG HOST_GID=1000
RUN if groupadd -g ${HOST_GID} app; then\
    useradd -m -s /bin/bash -u ${HOST_UID} app -g app; else\
    useradd -m -s /bin/bash -u ${HOST_UID} app; fi
# groupaddが失敗しても継続

# https://zenn.dev/rihito/articles/7b48821e4a3f74
# poetryのインストール先の指定
ENV POETRY_HOME=/opt/poetry
RUN curl -sSL https://install.python-poetry.org | python3 - &&\
    #一時的にget-poetry.shが使えない
    #RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python && \
    # シンボリックによるpathへのpoetryコマンドの追加
    cd /usr/local/bin && \
    ln -s /opt/poetry/bin/poetry && \
    # 仮想環境を作成しない設定(コンテナ前提のため，仮想環境を作らない)
    poetry config virtualenvs.create false
RUN chmod 777 /opt/poetry/bin/poetry
RUN chown -R app:app /usr/src

COPY --chown=app:app pyproject.toml .
COPY --chown=app:app poetry.lock .

# poetryでライブラリをインストール
RUN poetry install --no-root
RUN poetry config virtualenvs.create false

CMD ["python", "main.py"]
