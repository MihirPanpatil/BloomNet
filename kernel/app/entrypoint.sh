#!/bin/sh
# start kernel (no tailscale in this image by default; Tailscale instructions are below)
exec uvicorn main:app --host 0.0.0.0 --port 8000