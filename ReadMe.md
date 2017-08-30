This is an EAGI script written in Python to test interactions between AWS Lex and Asterisk

EAGI is used to collect audio input from file descriptor 3

Permissions: Make sure your lex-exec-roll has permissions for polly:* so that you can synthesize speech. Even though the Bot may have been created with an IAM user that has polly:SynthesizeSpeech permissions, the bot will use lex-exec-roll which does not right out of the gate. Really annoying but Lex is still beta I guess.

If you have additional variables that need to be replaced in the asterisk conf files, add them to confvars.csv,
otherwise they will be ignored. This prevents shell formatted dialplan variables in extensions.conf from being blanked.

If you are installing on an instance that already has credentials, ignore the following:
In order for the script to function, you need to place your AWS credentials into an env file under environments/

Format as:
```
export AWS_ACCESS_KEY_ID=<Your AWS Access Key Id>
export AWS_SECRET_ACCESS_KEY=<Your AWS Secret Access Key>
export AWS_SESSION_TOKEN=<Your AWS Session Token>
export AWS_DEFAULT_REGION=<Region of deployment, but right now LEX only works in us-east-1>
```

Additional configuration documentation goes... here!