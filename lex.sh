#! /bin/bash

# If there are environment files, source them
if [ -e "/tmp/environments/*"]
then
  for $source in /tmp/environments/* ; do
    . $source
  done
fi

if [ -e "/tmp/confs/*.conf" ]
then
  # run envsubst on custom confs
  for template in /tmp/confs/*.conf ; do
  # file=$(echo $template | sed -e 's/\.template$//')
  envsubst < $template > /etc/asterisk/$template
  done
fi

/usr/sbin/asterisk -fvvvvv