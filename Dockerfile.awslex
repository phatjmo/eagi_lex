FROM respoke/asterisk:14
# FROM respoke/asterisk:13.5
MAINTAINER Justin Zimmer <jzimmer@leasehawk.com>

RUN apt-get update -qq
RUN apt-get install --no-install-recommends --no-install-suggests -qqy \
    bash \
    python2.7 \
    python-pip \
    gettext
RUN pip install pyst2
RUN pip install boto3

COPY confs/*.conf /tmp/confs/
COPY environments/*.env /tmp/environments/
COPY *.py /etc/asterisk/eagi/
COPY lex.sh /
COPY confvars.csv /
RUN chmod +x /lex.sh
RUN chmod +x /etc/asterisk/eagi/*.py
CMD /lex.sh
