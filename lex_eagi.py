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
CONTENT_TYPE = 'audio/l16; rate=16000; channels=1'
ACCEPT = 'audio/pcm'
PERSIST_DIALOG = ['ElicitIntent', 'ConfirmIntent', 'ElicitSlot']
# Polly Params
POLLY_OUTPUT_FORMAT = "pcm"
POLLY_VOICE_ID = os.environ['POLLY_VOICE_ID'] # "salli"
AUDIO_FORMATS = {"ogg_vorbis": "audio/ogg",
                 "mp3": "audio/mpeg",
                 "pcm": "audio/wave; codecs=1"}
CHUNK_SIZE = 1024
HTTP_STATUS = {"OK": ResponseStatus(code=200, message="OK"),
               "BAD_REQUEST": ResponseStatus(code=400, message="Bad request"),
               "NOT_FOUND": ResponseStatus(code=404, message="Not found"),
               "INTERNAL_SERVER_ERROR": ResponseStatus(code=500, message="Internal server error")}

# API Objects
LEX = boto3.client('lex-runtime')
POLLY = boto3.client('polly')


def serializeSessionAttributes():
  return base64.b64encode(json.dumps({})) # Important stuff will need to go here regarding the session attributes

def read_text(text):
  """Handles routing for reading text (speech synthesis)"""
  # Get the parameters from the query string
  voiceId = POLLY_VOICE_ID
  outputFormat = POLLY_OUTPUT_FORMAT

  # Validate the parameters, set error flag in case of unexpected
  # values
  if len(text) == 0 or len(voiceId) == 0 or \
    outputFormat not in AUDIO_FORMATS:
    raise HTTPStatusError(HTTP_STATUS["BAD_REQUEST"],
                              "Wrong parameters")
  else:
    try:
      # Request speech synthesis
      response = POLLY.synthesize_speech(Text=text,
                                          VoiceId=voiceId,
                                          OutputFormat=outputFormat)
    except (BotoCoreError, ClientError) as err:
      # The service returned an error
      raise HTTPStatusError(HTTP_STATUS["INTERNAL_SERVER_ERROR"], str(err))

    # return ResponseData(status=HTTP_STATUS["OK"],
    #                     content_type=AUDIO_FORMATS[outputFormat],
    #                     # Access the audio stream in the response
    #                     data_stream=response.get("AudioStream"))
    return response.get("AudioStream")


def startAGI():
  dialogState = "";
  agi = AGI()
  agi.verbose("Lex EAGI script started...")
  ani = agi.env['agi_callerid']
  did = agi.env['agi_extension']
  # audio_in = io.open(AUDIO_FD, mode=r) # Vanilla IO stream...
  # Wait for silence here?
  agi.answer()
  agi.stream_file(read_text("Hello, I am an automated assistant for BuyMyEffinFlowers.Com, how may I help you?"))
  while dialogState not in PERSIST_DIALOG:
    audio_in = wave.open(AUDIO_FD, 'r') # wave library wave_read reader...
    try:
      agi.verbose("Connecting to: %s" % (LEX))
      response = LEX.post_content(
          botName=BOT_NAME,
          botAlias=BOT_ALIAS,
          userId=ani,
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
      dialogState = response.get("dialogState")
      agi.stream_file(response.get("audioStream"))
      agi.verbose(dialogState)
      agi.verbose(response.get("message"))
    except (BotoCoreError, ClientError) as err:
      # The service returned an error
      # raise HTTPStatusError(HTTP_STATUS["INTERNAL_SERVER_ERROR"],
      #                           str(err))
      agi.verbose("Could not engage Lex because of: %s", (err))
      agi.stream_file('cannot-complete-network-error')
      agi.hangup()
      exit(1)
# Extras
  # agi.stream_file('cannot-complete-network-error')
  # agi.hangup()
  # exit(1)

  # agi.set_callerid(outANI)
  # agi.set_variable("CAMPAIGN", campaign)
  # agi.set_variable("EMPLOYEE", empID) 
  agi.verbose("Lex interaction complete " % (response))
  exit()


startAGI()