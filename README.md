# Project Setup

To run the project, use the following command:

```sh
python -m gunicorn config.asgi:application -k uvicorn.workers.UvicornWorker
```
