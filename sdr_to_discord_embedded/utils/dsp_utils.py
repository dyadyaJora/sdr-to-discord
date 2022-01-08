import numpy as np
import scipy.signal as signal


def fm_de_mod(data):
    sigif = signal.decimate(data, 5, ftype='iir')
    phase = np.unwrap(np.angle(sigif))
    pd = np.convolve(phase, [1, -1], mode='valid')
    audio = signal.decimate(pd, 10, ftype='iir')
    return audio


def float_to_pcm16(audio):
    ints = (audio * 32767).astype(np.int16)
    little_endian = ints.astype('<u2')
    buf = little_endian.tostring()
    return buf


def int32_to_pcm16(audio):
    ints = (audio / 2147483647 * 32767).astype(np.int16)
    little_endian = ints.astype('<u2')
    buf = little_endian.tostring()
    return buf