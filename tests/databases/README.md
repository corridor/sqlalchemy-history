This directory contains Docker Compose files for running the test suite against
the same database images and connection settings used in GitHub Actions.

## Working with different databases

Start the desired database, wait for its health check to pass, and run
`uv run pytest --db=<database>`, where `<database>` is `sqlite` (default), `postgres`, `mysql`, `mssql` or `oracle`.

To ensure you have docker available in your system run below commands first make sure that you have docker-engine
running in your local or docker service is started in your linux system.

- **_docker_** : `docker ps` shows list of active containers in your system if this commands throws no error like
  command not found, that means you have docker in your system

Use following Commands to initiate different DB in your local, and you can use this deployed DB to either test or
run application on top of it all you have to do is update respective settings file with Apt. URI of DB so that
application or testing suite can connect with this DB

Helpful commands for working with docker containers

- `docker ps`: gives you list of active running containers.
- `docker ps -a`: gives you list of active and crashed containers.
- `docker images`: gives images that you have in your local pulled from docker-hub or any image repository
- `docker stop <CONTAINER_ID | CONTAINER_NAME>`: stops the running container
- `docker logs <CONTAINER_ID | CONTAINER_NAME>`: get container logs
- `docker compose ... -d`: -d runs the docker in daemon mode. To see logs, remove -d

We don't have requirement to setup network configurations for these containers so we are setting default docker network setting

### Oracle

Backend support Oracle 19+, for test suite we use oracle:21 as it is publicly available image in express edition.
to run oracle DB use either of below commands

```bash
docker compose -f tests/databases/docker-compose.oracle.yml up -d
```

The test suite connects with
`oracle+oracledb://SYSTEM:Oracle2022@localhost:1521/?service_name=XEPDB1`.

Image Details : https://hub.docker.com/r/gvenzl/oracle-xe

### MSSQL

Backend support MSSQL 2016+, for test suite we use mssql:2017 as mssql 2016 docker image is not available.
To run MSSQL DB use either of below commands

```bash
docker compose -f tests/databases/docker-compose.mssql.yml up -d
```

The test suite connects with
`mssql+pyodbc://sa:MSsql2022@localhost:1433/master?driver=ODBC+Driver+17+for+SQL+Server&TrustServerCertificate=yes`.

Image Details : https://mcr.microsoft.com/en-us/product/mssql/server/about

**_NOTE_**: We are not able to create new user for MSSQL DB as it does not allow to do this via configuring while running
however we have option to do this by customizing the entrypoint.sh where we can create new DB and new User while running
refer: https://github.com/microsoft/mssql-docker/tree/master/linux/preview/examples/mssql-customize

### Postgres

The PostgreSQL test service tracks the current official `postgres` image.
to run Postgres DB use either of below commands
docker command:

```bash
docker compose -f tests/databases/docker-compose.postgresql.yml up -d
```

The test suite connects with
`postgresql://postgres:postgres@localhost:5432/sqlalchemy_history_test`.

Image Details : https://hub.docker.com/_/postgres/

## Installing docker in WSL

Example instructions to install Ubuntu 24.04 in WSL.
Any alternative installation steps should be fine too, we just need a working docker.
Ref: https://dev.to/bartr/install-docker-on-windows-subsystem-for-linux-v2-ubuntu-5dl7

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y apt-transport-https ca-certificates curl software-properties-common

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo usermod -aG docker $USER

# Restart WSL by running this in a powershell:
# wsl --shutdown

docker run hello-world
```
