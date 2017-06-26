#! /bin/bash/python
import os
import io
import wave
import base64
import json
import asterisk.agi
import boto3
"""

Connect to AWS Lex using Boto3 and send PCM audio stream.

"""
__author__ = 'Justin Zimmer'

AUDIO_FD = 3
BOT_NAME = os.environ['LEX_BOT_NAME']
BOT_ALIAS = os.environ['LEX_BOT_ALIAS'] # Really not sure what to put here yet...
USER_ID = os.environ['LEX_USER_ID']
CONTENT_TYPE = 'audio/l16; rate=16000; channels=1'
ACCEPT = 'audio/pcm'
LEX = boto3.client('lex-runtime')

def serializeSessionAttributes():
  return base64.b64encode(json.dumps({})) # Important stuff will need to go here regarding the session attributes

def startAGI():
  agi = AGI()
  agi.verbose("Lex EAGI script started...")
  ani = agi.env['agi_callerid']
  did = agi.env['agi_extension']
  # audio_in = io.open(AUDIO_FD, mode=r) # Vanilla IO stream...
  audio_in = wave.open(AUDIO_FD, 'r') # wave library wave_read reader...
  # Wait for silence here?

  try:
    agi.verbose("Connecting to: %s" % (LEX))
    response = LEX.post_content(
        botName='ACE',
        botAlias='ACE Bot',
        userId=USER_ID,
        contentType=CONTENT_TYPE,
        sessionAttributes=serializeSessionAttributes(),
        accept=ACCEPT,
        inputStream=audio_in.readframes(10) # I really don't know how many frames to check for!
    )
    # Expecting:
    # {
    #     'contentType': 'string',
    #     'intentName': 'string',
    #     'slots': {...}|[...]|123|123.4|'string'|True|None,
    #     'sessionAttributes': {...}|[...]|123|123.4|'string'|True|None,
    #     'message': 'string',
    #     'dialogState': 'ElicitIntent'|'ConfirmIntent'|'ElicitSlot'|'Fulfilled'|'ReadyForFulfillment'|'Failed',
    #     'slotToElicit': 'string',
    #     'inputTranscript': 'string',
    #     'audioStream': StreamingBody()
    # }

  except Exception e:
    agi.verbose("Could not send audio to Lex!!!")
    agi.stream_file('cannot-complete-network-error')
    agi.hangup()
    exit(1)

  agi.stream_file('cannot-complete-network-error')
  agi.hangup()
  exit(1)

  agi.set_callerid(outANI)
  agi.set_variable("CAMPAIGN", campaign)
  agi.set_variable("EMPLOYEE", empID)
  agi.verbose("Lex interaction complete " % (response))
  exit()


startAGI()


