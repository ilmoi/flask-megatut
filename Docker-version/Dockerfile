FROM python:3.6-alpine

# it's not good practice to run the application as root user so we create our own
RUN adduser -D microblog

# set a default directory where the app will be installed
WORKDIR /home/microblog

COPY requirements.txt requirements.txt
RUN python -m venv venv
RUN venv/bin/pip install -r requirements.txt
RUN venv/bin/pip install gunicorn pymysql

COPY app app
COPY migrations migrations
COPY microblog.py config.py boot.sh ./
#ensure boot.sh is executable
RUN chmod +x boot.sh

ENV FLASK_APP microblog.py

# change the user of all the files we just moved to be microblog (which we just created)
RUN chown -R microblog:microblog ./
# then switch over to that user
USER microblog

# how the container is exposed
EXPOSE 5000
# what command is executed when container is started
ENTRYPOINT ["./boot.sh"]