FROM nginx:1.25-alpine

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d

RUN apk add --update apache2-utils \
    && rm -rf /var/cache/apk/*
