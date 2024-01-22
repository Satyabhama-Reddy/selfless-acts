FROM alpine:3.7
ENV TEAM_ID=CC_124_143_162_173
ADD common /common

RUN apk add --no-cache python3-dev \
    && pip3 install --upgrade pip \
    && pip3 install flask-restful
RUN pip3 install flask
EXPOSE 80

CMD ["/common/runner.sh"]
