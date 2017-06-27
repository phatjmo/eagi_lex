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
        # with wave.open(output[1], 'w') as file:
        # file.setnchannels(1)
        # file.setsampwidth(2)
        # file.setframerate(8000)
        # file.writeframes(stream.read())
        file.write(stream.read())

      return os.path.splitext(output[1])[0]
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
    with open(output[1], 'wb') as file:
      # with wave.open(output[1], 'w') as file:
      # file.setnchannels(1)
      # file.setsampwidth(2)
      # file.setframerate(8000)
      # file.writeframes(stream.read())
      file.write(audio_bytes)
    return os.path.splitext(output[1])[0]
      # return output
  except IOError as error:
    # Could not write to file, exit gracefully
    # print error
    return 'cannot-complete-network-error'

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
  # print response
  if "AudioStream" in response:
    # Note: Closing the stream is important as the service throttles on the
    # number of parallel connections. Here we are using contextlib.closing to
    # ensure the close method of the stream object will be called automatically
    # at the end of the with statement's scope.
    return stream_to_file(response["AudioStream"])
    # with closing(response["AudioStream"]) as stream:
    #   output = mkstemp(suffix=".sln16")
    #   try:
    #     # Open a file for writing the output as a binary stream
    #     # return stream.read()
    #     with open(output[1], 'wb') as file:
    #     # with wave.open(output[1], 'w') as file:
    #       # file.setnchannels(1)
    #       # file.setsampwidth(2)
    #       # file.setframerate(8000)
    #       # file.writeframes(stream.read())
    #       file.write(stream.read())
    #     return os.path.splitext(output[1])[0]
    #     # return output
    #   except IOError as error:
    #     # Could not write to file, exit gracefully
    #     # print error
    #     return 'cannot-complete-network-error'

  else:
  # The response didn't contain audio data, exit gracefully
    # print "Could not stream audio"
    # sys.exit(-1)
    return 'cannot-complete-as-dialed'


def startAGI():
  dialogState = "BeginInteraction"
  agi = AGI()
  agi.verbose("Lex EAGI script started...")
  ani = agi.env['agi_callerid']
  did = agi.env['agi_extension']
  # audio_in = io.open(AUDIO_FD, mode=r) # Vanilla IO stream...
  # Wait for silence here?
  agi.answer()
  agi.verbose("Call answered from: %s to %s" % (ani, did))
  # try:
  agi.stream_file(read_text(POLLY_GREETING))
  # os.read(AUDIO_FD, 320000)

  # except Exception as e:
  #   agi.verbose(e)
  #   agi.stream_file('tt-somethingwrong')
  #   agi.hangup()
  #   exit(1)
  agi.verbose("Streamed TTS: %s" % (POLLY_GREETING))
  agi.verbose("Attempting to play back FD %d audio" %(AUDIO_FD))
  # grab_intent = os.fdopen(AUDIO_FD, 'rb')
  # audio_in = os.read(AUDIO_FD, 80000)
  # agi.stream_file('spy-jingle')
  # agi.stream_file(bytes_to_file(grab_intent.read(65000)))
  # grab_intent.read(9999999)
  # agi.stream_file('spy-jingle')
  while dialogState in PERSIST_DIALOG:
    # audio_in = os.read(AUDIO_FD, 160000)
    # audio_in = wave.open(AUDIO_FD, 'r') # wave library wave_read reader...
    test = os.read(AUDIO_FD, 1024000) # try to force FD to end...
    try:
      # os.write(AUDIO_FD+1, "") # See if the write is one up...

      # afile = AudioRawStream(os.fdopen(3, 'rb'), SAMPLE_WIDTH, SAMPLE_RATE)
      test = os.read(AUDIO_FD, 1024000)
      sleep(4)
      # agi.verbose("Connecting to: %s" % (LEX))
      # os.lseek(AUDIO_FD, 0, os.SEEK_END)
      # grab_intent = os.read(AUDIO_FD, 1024000)
      # agi.verbose("Length of intent: %d" % (grab_intent.__len__()))
      # playback intent
      # agi.stream_file(bytes_to_file(grab_intent))
      test = os.read(AUDIO_FD, 1024000)
      agi.stream_file(bytes_to_file(test))
      response = LEX.post_content(
          botName=BOT_NAME,
          botAlias=BOT_ALIAS,
          userId=ani,
          contentType=CONTENT_TYPE,
          # sessionAttributes=serializeSessionAttributes(),
          accept=ACCEPT,
          # inputStream=audio_in.readframes(10) # I really don't know how many frames to check for!
          inputStream=convert_to_lex(test)
          # inputStream=grab_intent.read(65000)
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
      # print response
      dialogState = response.get("dialogState")
      agi.stream_file(stream_to_file(response.get("audioStream")))
      agi.verbose("Interaction status: %s" % (dialogState))
      agi.verbose("Lex says: %s" % (response.get("message")))
      agi.verbose("You said: %s" % (response.get("inputTranscript")))
    except (BotoCoreError, ClientError) as err:
      # The service returned an error
      # raise HTTPStatusError(HTTP_STATUS["INTERNAL_SERVER_ERROR"],
      #                           str(err))
      agi.verbose("Could not engage Lex because of: %s" % (err))
      agi.stream_file('cannot-complete-network-error')
      agi.hangup()
      grab_intent.close()
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
  grab_intent.close()
  exit()


startAGI()