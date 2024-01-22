FROM alpine:3.7
ENV TEAM_ID=CC_124_143_162_173
ADD common /common
RUN apk add python3-dev
RUN pip3 install --upgrade pip 
RUN pip3 install flask-restful
RUN pip3 install flask
RUN pip3 install requests
EXPOSE 80

CMD ["/common/runner.sh"]
