# Juudge API

This project provides a simple API to ask questions about the MTG Card Game

It requires an OpenAPI API Key to work.

## Dev Containers

The project requires a PGVector database to work. To streamline the development
process, the project contains a "dev-container" dedfinition in the
".devcontainer" subfolder.

When working with dev-containers, this will provide the full stack necessary to
work on the project with all config-values readily set up (except the OpenAI
API-key).

## Initial Environment Bootstrap

Create a virtual environment and install the project:

```
python3 -m venv env
./env/bin/pip install -e .
```

## Running

To run the application, you must set the following environment variables:

- `JUUDGE_DSN`: A "psycopg" compatible connection string to a "pgvector"
    database.
    For example: `postgresql+psycopg://langchain:langchain@database/langchain`
- `JUUDGE_SECRET_KEY`: A sufficiently long and random string to securely sign
    authentication tokens.
- `JUUDGE_USERNAME`: The username that is accepted to log-in
- `JUUDGE_PASSWORD`: The password for the given username

Then run the application:

```
./env/bin/uvicorn \
  --factory juudge.web.web:create_app \
  --reload
```

# Authenticating

The API currently requires authentication. The current (limited) implementation
works by firs sending a `POST` reques to `/token` using the username and
password defined in the environment variables. An example document to submit
looks like this:

```
{"username": "john.doe", "password": "secret"}
```

The return-value from this call contains a JWT token that must then be sent on
each request in the `Authorization` header. For example:

```
Authorization: Bearer <my-token>
```

# Loading Data

The application is written to ingest data from two sources:

- The MTG-Json "Atomic" format (see https://mtgjson.com/api/v5/)
- The plain-text core ruleset (see https://magic.wizards.com/en/rules)

The API includes the SwaggerUI that can be used to upload the files and it
should be fairly self-explanatory.
