#!/bin/sh
set -eu

envsubst '$VITE_API_BASE_URL $VITE_OIDC_AUTHORITY $VITE_OIDC_CLIENT_ID $VITE_OIDC_REDIRECT_URI $VITE_OIDC_POST_LOGOUT_REDIRECT_URI' \
  < /etc/vezor/frontend/config.template.js \
  > /usr/share/nginx/html/config.js
