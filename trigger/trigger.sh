#!/bin/bash

curl -sS -o /dev/null -w "HTTP %{http_code}\n" -X POST http://127.0.0.1:80/trigger