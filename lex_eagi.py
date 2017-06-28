#! /usr/bin/python
from collections import namedtuple
from contextlib import closing
from asterisk.agi import *
import os
import io
import wave
import audioop
import base64
import json
import boto3
# import speech_recognition as sr
from time import sleep
from botocore.exceptions import BotoCoreError, ClientError
from tempfile import gettempdir, mkstemp
"""

Connect to AWS Lex using Boto3 and send PCM audio stream.

"""
__author__ = 'Justin Zimmer'

ResponseStatus = namedtuple("HTTPStatus",
                            ["code", "message"])

ResponseData = namedtuple("ResponseData",
                          ["status", "content_type", "data_stream"])

AUDIO_FD = 3
BOT_NAME = os.getenv('LEX_BOT_NAME')
BOT_ALIAS = os.getenv('LEX_BOT_ALIAS') # Really not sure what to put here yet...
CONTENT_TYPE = 'audio/l16; rate=16000; channels=1'
#CONTENT_TYPE = 'audio/l16; rate=8000; channels=1'
ACCEPT = 'audio/pcm'
PERSIST_DIALOG = ['BeginInteraction', 'ElicitIntent', 'ConfirmIntent', 'ElicitSlot']
# Polly Params
POLLY_OUTPUT_FORMAT = "pcm"
POLLY_VOICE_ID = os.getenv('POLLY_VOICE_ID') # "salli"
POLLY_GREETING = "Hello, I am an automated assistant for BuyMyEffinFlowers.Com, how may I help you?"
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

SAMPLE_WIDTH, SAMPLE_RATE = 2.0, 18000.0 # 16-bit, 48kHz PCM audio

def serializeSessionAttributes():
  # Important stuff will need to go here regarding the session attributes
  return base64.b64encode(json.dumps({}))

def convert_to_lex(raw_input):
  test_wav = mkstemp(suffix=".wav")[1]
  writetemp = wave.open(test_wav,'wb')
  writetemp.setparams((1, 2, 16000, 0, 'NONE', 'not compressed'))
  converted = audioop.ratecv(raw_input, 2, 1, 8000, 16000, None)
  writetemp.writeframesraw(converted[0])
  writetemp.close()
  readtemp = wave.open(test_wav,'rb')
  frames = readtemp.readframes(readtemp.getnframes())
  # return audioop.tomono(converted[0], 2, 1, 0)
  readtemp.close()
  os.remove(test_wav)
  return frames
  

def stream_to_file(audio_stream):
  with closing(audio_stream) as stream:
    output = mkstemp(suffix=".sln16")
    try:
        # Open a file for writing the output as a binary stream
        # return stream.read()
      with open(output[1], 'wb') as file:
        file.write(stream.read())

      return output[1]
        # return output
    except IOError as error:
      # Could not write to file, exit gracefully
      # print error
      return 'cannot-complete-network-error'

def bytes_to_file(audio_bytes):
  output = mkstemp(suffix=".sln")
  try:
      # Open a file for writing the output as a binary stream
      # return stream.read()
    with open(output[1], 'wb') as audio:
      audio.write(audio_bytes)
    return output[1]
      # return output
  except IOError as error:
    # Could not write to file, exit gracefully
    # print error
    return 'cannot-complete-network-error'

def read_text(text):
  """Handles routing for reading text (speech synthesis)"""
  # Get the parameters from the query string
  voice_id = POLLY_VOICE_ID
  output_format = POLLY_OUTPUT_FORMAT

  # Validate the parameters, set error flag in case of unexpected
  # values
  if len(text) == 0 or len(voice_id) == 0 or \
    output_format not in AUDIO_FORMATS:
    raise HTTPStatusError(HTTP_STATUS["BAD_REQUEST"],
                          "Wrong parameters")
  else:
    try:
      # Request speech synthesis
      response = POLLY.synthesize_speech(Text=text,
                                         VoiceId=voice_id,
                                         OutputFormat=output_format)
    except (BotoCoreError, ClientError) as err:
      # The service returned an error
      raise HTTPStatusError(HTTP_STATUS["INTERNAL_SERVER_ERROR"], str(err))

    # return ResponseData(status=HTTP_STATUS["OK"],
    #                     content_type=AUDIO_FORMATS[outputFormat],
    #                     # Access the audio stream in the response
    #                     data_stream=response.get("AudioStream"))
  # print response
  if "AudioStream" in response:
    # Note: Closing the stream is important as the service throttles on the
    # number of parallel connections. Here we are using contextlib.closing to
    # ensure the close method of the stream object will be called automatically
    # at the end of the with statement's scope.
    return stream_to_file(response["AudioStream"])
  else:
    # The response didn't contain audio data, exit gracefully
    return 'cannot-complete-as-dialed'

def startAGI():
  """
  Begin AGI Processing
  """

  dialog_state = "BeginInteraction"
  agi = AGI()
  agi.verbose("Lex EAGI script started...")
  ani = agi.env['agi_callerid']
  did = agi.env['agi_extension']
  # audio_in = io.open(AUDIO_FD, mode=r) # Vanilla IO stream...
  # Wait for silence here?
  agi.answer()
  agi.verbose("Call answered from: %s to %s" % (ani, did))
  # try:
  greet_file = read_text(POLLY_GREETING)
  agi.stream_file(os.path.splitext(greet_file)[0])
  os.remove(greet_file)
  agi.verbose("Streamed TTS: %s" % (POLLY_GREETING))
  while dialog_state in PERSIST_DIALOG:
    # audio_in = os.read(AUDIO_FD, 160000)
    # audio_in = wave.open(AUDIO_FD, 'r') # wave library wave_read reader...
    test = os.read(AUDIO_FD, 1024000) # clear buffer
    try:
      # os.write(AUDIO_FD+1, "") # See if the write is one up...

      # afile = AudioRawStream(os.fdopen(3, 'rb'), SAMPLE_WIDTH, SAMPLE_RATE)
      test = os.read(AUDIO_FD, 1024000) # clear buffer again
      test = ""
      sleep(4)
      intent = os.read(AUDIO_FD, 1024000) # grab buffer
      intent_audio = bytes_to_file(intent)
      agi.stream_file(os.path.splitext(intent_audio)[0]) # Playback to verify sample
      os.remove(intent_audio)
      response = LEX.post_content(
          botName=BOT_NAME,
          botAlias=BOT_ALIAS,
          userId=ani,
          contentType=CONTENT_TYPE,
          # sessionAttributes=serializeSessionAttributes(),
          accept=ACCEPT,
          inputStream=convert_to_lex(intent)
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

      dialog_state = response.get("dialogState")
      response_audio = stream_to_file(response.get("audioStream"))
      agi.stream_file(os.path.splitext(response_audio)[0])
      os.remove(response_audio)
      agi.verbose("Interaction status: %s" % (dialog_state))
      agi.verbose("Lex says: %s" % (response.get("message")))
      agi.verbose("You said: %s" % (response.get("inputTranscript")))
    except (BotoCoreError, ClientError) as err:
      agi.verbose("Could not engage Lex because of: %s" % (err))
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

  agi.verbose("Lex interaction complete")
  agi.hangup()
  exit()


startAGI()
