#! /bin/bash
echo 'Setting up environment and running Asterisk!'
# If there are environment files, source them
# if [ -e "/tmp/environments/*"]
# then
  for source in /tmp/environments/*.env ; do
    echo "Sourcing $source"
    . $source
  done
# fi

# if [ -e /tmp/confs/*.conf ]
# then
  # run envsubst on custom confs
  cd /tmp/confs/
  for template in *.conf ; do
    echo "Deleting existing $template from /etc/asterisk"
    rm -f /etc/asterisk/$template
    # file=$(echo $template | sed -e 's/\.template$//')
    echo "Substituting variables in $template"
    # Must put variables that need to be replaced in asterisk conf files in confvars.csv
    # Otherwise extensions.conf variables get blanked
    envsubst $(cat /confvars.csv) < $template > /etc/asterisk/$template
    echo "Fixing Asterisk variables in $template"
    # cp $template /etc/asterisk
  done
# fi

/usr/sbin/asterisk -fvvvvv