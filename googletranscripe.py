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
# Imports the Google Cloud client library
from google.cloud import speech
# import speech_recognition as sr
from time import sleep
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
CONTENT_TYPE = 'audio/l16; rate=16000; channels=1'
#CONTENT_TYPE = 'audio/l16; rate=8000; channels=1'
ACCEPT = 'audio/pcm'
AUDIO_FORMATS = {"ogg_vorbis": "audio/ogg",
                 "mp3": "audio/mpeg",
                 "pcm": "audio/wave; codecs=1"}
CHUNK_SIZE = 1024
HTTP_STATUS = {"OK": ResponseStatus(code=200, message="OK"),
               "BAD_REQUEST": ResponseStatus(code=400, message="Bad request"),
               "NOT_FOUND": ResponseStatus(code=404, message="Not found"),
               "INTERNAL_SERVER_ERROR": ResponseStatus(code=500, message="Internal server error")}

# API Objects
speech_client = speech.Client()

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
  agi.verbose("Google transcribe script started...")
  ani = agi.env['agi_callerid']
  did = agi.env['agi_extension']
  agi.answer()
  agi.verbose("Call answered from: %s to %s" % (ani, did))
  
  agi.stream_file('please-say-name')
  agi.verbose("Streamed TTS: %s" % (POLLY_GREETING))
  test = os.read(AUDIO_FD, 1024000) # clear buffer
  sample = speech_client.sample(
      test,
      source_uri=None,
      encoding='LINEAR16',
      sample_rate_hertz=8000)

  # Detects speech in the audio file
  alternatives = sample.recognize('en-US')

  for alternative in alternatives:
    agi.verbose('Transcript: %s' % (alternative.transcript))

# Extras
  # agi.stream_file('cannot-complete-network-error')
  # agi.hangup()
  # exit(1)

  # agi.set_callerid(outANI)
  # agi.set_variable("CAMPAIGN", campaign)
  # agi.set_variable("EMPLOYEE", empID)

  agi.verbose("Google transcription complete")
  agi.hangup()
  exit()


startAGI()
