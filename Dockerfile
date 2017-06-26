FROM respoke/asterisk14
MAINTAINER Justin Zimmer <jzimmer@leasehawk.com>

RUN apt-get install python2.7 python-pip
RUN pip install pyst2
RUN pip install boto3

COPY confs/*.conf /tmp/confs/
COPY environments/*.env /tmp/environments/
COPY lex_eagi.py /etc/asterisk/eagi/
COPY lex.sh /
CMD /lex.sh
