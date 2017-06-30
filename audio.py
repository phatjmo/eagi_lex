
import wave
import audioop
import contextlib
import tempfile
import shutil
from os import path, makedirs


def gen_sine_wav(filename, rate=44100, channels=2, bits=16, length=30):
    """
    Generate a Sine Wav test file using wavebender.
    """
    import sys
    from mod.util import wavebender

    frequency = 440.0
    amplitude = 0.5

    # each channel is defined by infinite functions which are added to produce a sample.
    channels = ((wavebender.sine_wave(frequency, rate, amplitude),) for i in range(channels))

    # convert the channel functions into waveforms
    samples = wavebender.compute_samples(channels, rate * length)

    # write the samples to a file
    if filename == '-':
        filename = sys.stdout

    wavebender.write_wavefile(filename, samples, rate * length, channels, bits / 8, rate)
    return path.exists(filename)

def make_test_wav(rate=44100, channels=2, bits=16, length=30):
    """
    Generate noisy wav file for use in unit tests.

    -- Doctest --

    >>> import os
    >>> test1 = make_test_wav(11025, 1, 8, 5)
    >>> test2 = make_test_wav(11025, 2, 8, 5)
    >>> test3 = make_test_wav(11025, 1, 16, 5)
    >>> test4 = make_test_wav(11025, 2, 16, 5)
    >>> check_format(test1, 11025, 1, 8)
    True
    >>> check_format(test2, 11025, 2, 8)
    True
    >>> check_format(test3, 11025, 1, 16)
    True
    >>> check_format(test4, 11025, 2, 16)
    True
    >>> wav_duration(test1)
    5
    >>> wav_duration(test2)
    5
    >>> wav_duration(test3)
    5
    >>> wav_duration(test4)
    5
    >>> os.remove(test1)
    >>> os.remove(test2)
    >>> os.remove(test3)
    >>> os.remove(test4)
    """
    import random
    import struct

    test_wav = tempfile.mkstemp(suffix=".wav")[1]
    samp_width = bits/8
    if samp_width == 1:
        c_type = 'b'
    else:
        c_type = 'h'

    sample_len = rate * length # * channels * samp_width
    noise_output = wave.open(test_wav, 'w')
    noise_output.setparams((channels, samp_width, rate, 0, 'NONE', 'not compressed'))
    range_end = float(int((2 ** bits) / 2) - 1)
    range_start = range_end * -1

    values = []

    for sample in range(0, sample_len):
        __ignore = sample # Make PyLint Happy
        value = random.randint(range_start, range_end)
        packed_value = struct.pack(c_type, value)
        for tick in range(channels):
            __ignore = tick
            values.append(packed_value)

    value_str = ''.join(values)
    noise_output.writeframes(value_str)

    noise_output.close()
    return test_wav

def wav_duration(vm_file):
    """
    Returns the length of the VM Wav file.

    -- Doctest --

    >>> import os
    >>> test1 = make_test_wav(11025, 1, 8, 5)
    >>> test2 = make_test_wav(11025, 2, 8, 5)
    >>> test3 = make_test_wav(11025, 1, 16, 5)
    >>> test4 = make_test_wav(11025, 2, 16, 5)
    >>> check_format(test1, 11025, 1, 8)
    True
    >>> check_format(test2, 11025, 2, 8)
    True
    >>> check_format(test3, 11025, 1, 16)
    True
    >>> check_format(test4, 11025, 2, 16)
    True
    >>> wav_duration(test1)
    5
    >>> wav_duration(test2)
    5
    >>> wav_duration(test3)
    5
    >>> wav_duration(test4)
    5
    >>> os.remove(test1)
    >>> os.remove(test2)
    >>> os.remove(test3)
    >>> os.remove(test4)
    """

    if path.isfile(vm_file):
        with contextlib.closing(wave.open(vm_file, 'r')) as wav:
            frames = wav.getnframes()
            rate = wav.getframerate()
            duration = (frames / float(rate))
            return int(duration)
    else:
        return -1

def check_format(vm_file, rate=11025, channels=1, bits=16):
    """
    Check if the specified Wav recording is in an Asterisk Compatible format.

    -- Doctest --

    >>> import os
    >>> test = make_test_wav(44100, 2, 16)
    >>> check_format(test, 11025, 1, 16)
    False
    >>> check_format(test, 44100, 2, 16)
    True
    >>> os.remove(test)
    """
    if not path.isfile(vm_file):
        return False

    wav_read = wave.open(vm_file, 'r')
    wav_rate = wav_read.getframerate()
    wav_channels = wav_read.getnchannels()
    wav_frames = wav_read.getnframes()
    wav_width = wav_read.getsampwidth()
    wav_length = wav_duration(vm_file)
    width = bits/8
    frames = rate * wav_length
    if (wav_rate, wav_channels, wav_width, wav_frames) == (rate, channels, width, frames):
        return True
    else:
        return False

def wav_convert(src, dst, out_rate=11025, out_channels=1, out_bits=16):
    """
    Convert Wav file to specified format.
    Defaults represent Asterisk requirements for PCM.

    -- Doctest--

    >>> import os
    >>> import tempfile
    >>> test = make_test_wav(44100, 2, 16)
    >>> test2 = tempfile.mkstemp()[1]
    >>> check_format(test, 11025, 1, 16)
    False
    >>> wav_convert(test, test2, 11025, 1, 16)
    True
    >>> check_format(test2, 11025, 1, 16)
    True
    >>> os.remove(test)
    >>> os.remove(test2)
    """
    if not path.isfile(src):
        print 'Source not found!'
        return False


    if not path.exists(path.dirname(dst)):
        makedirs(path.dirname(dst))

    try:
        s_read = wave.open(src, 'r')
        s_write = wave.open(dst, 'w')
    except:
        print 'Failed to open files!'
        return False

    in_rate = s_read.getframerate()
    in_channels = s_read.getnchannels()
    in_width = s_read.getsampwidth()
    out_width = out_bits/8
    if (in_rate, in_channels, in_width) == (out_rate, out_channels, out_width):
        return True

    n_frames = s_read.getnframes()
    data = s_read.readframes(n_frames)

    try:
        converted = audioop.ratecv(data, out_width, in_channels, in_rate, out_rate, None)
        if out_channels == 1:
            converted = audioop.tomono(converted[0], 2, 1, 0)
    except:
        print 'Failed to downsample wav'
        return False

    try:
        s_write.setparams((out_channels, 2, out_rate, 0, 'NONE', 'Uncompressed'))
        s_write.writeframes(converted)
    except:
        print 'Failed to write wav'
        return False

    try:
        s_read.close()
        s_write.close()
    except:
        print 'Failed to close wav files'
        return False

    return True

def test_file(vm_file):
    """
    Make sure the vm_file for this campaign exists and is in the right format!

    -- Doctest--

    >>> import os
    >>> test = make_test_wav()
    >>> check_format(test)
    False
    >>> test_file(test)
    ('VERIFIED', 'File was converted successfully!')
    >>> check_format(test)
    True
    >>> os.remove(test)
    """
    import os
    allowed_types = ["wav", "ulaw", "alaw", "g729", "gsm"]
    file_type = os.path.splitext(vm_file)[1][1:].lower()
    if not os.path.isfile(vm_file):
        return ("NO_FILE", "File: {0} does not exist!".format(vm_file))

    if file_type == '' and not check_format(vm_file):
        return ("BAD_FILE", "Invalid file type or format!")

    if file_type not in allowed_types:
        return ("WRONG_TYPE", "File type: {0} is not allowed.".format(file_type))

    if file_type == "wav" and not check_format(vm_file):
        tmp_file = tempfile.mkstemp()[1]
        if not wav_convert(vm_file, tmp_file):
            return ("BAD_FORMAT", "File of type {0} is in an invalid format.".format(file_type))
        else:
            if check_format(tmp_file):
                os.remove(vm_file)
                shutil.move(tmp_file, vm_file)
                return ("VERIFIED", "File was converted successfully!")
            else:
                os.remove(tmp_file)
                return ("BAD_FORMAT",
                        "File of type {0} is in an invalid format and could not be converted."
                        .format(file_type))


    return ("VERIFIED",
            "File of type {0} is in an acceptable format, no changes were necessary."
            .format(file_type))


if __name__ == "__main__":
    import doctest
    doctest.testmod()
