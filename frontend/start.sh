#!/bin/sh
# Default to local Docker gateway if GATEWAY_URL not set
: "${GATEWAY_URL:=http://gateway:8000}"
envsubst '${GATEWAY_URL}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf
exec nginx -g 'daemon off;'
