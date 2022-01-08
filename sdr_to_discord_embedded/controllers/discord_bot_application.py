import math
import discord
import rtlsdr
import queue
import threading
import time
import opuslib

import scipy.signal as signal
import numpy as np

from sdr_to_discord_embedded.utils import dsp_utils


class DiscordBotApplication:
    def __init__(self, client_id, ffmpeg_path):
        self.client_id = client_id
        self.ffmpeg_path = ffmpeg_path

        self.sdr = None
        self.sdr_thread = None
        self.discord_thread = None
        self.que = None

    def start(self):
        client = discord.Client()

        @client.event
        async def on_ready():
            print('We have logged in as {0.user}'.format(client))

        @client.event
        async def on_message(message):
            global voice_client
            if message.author == client.user:
                return

            if message.content.startswith('$hello'):
                await message.channel.send('Hello!')

            if message.content.startswith('$voice-up'):
                voice_channel = message.guild.voice_channels[0]
                voice_client = await voice_channel.connect()
                audio_source = discord.FFmpegPCMAudio(source='tmp.mp3', executable=self.ffmpeg_path)
                voice_client.play(audio_source, after=lambda e: print('done', e))
                print('here')

            if message.content.startswith('$voice-down'):
                voice_channel = message.guild.voice_channels[0]
                await voice_client.disconnect()
                print('here')

            if message.content.startswith('$sdr-up'):
                voice_channel = message.guild.voice_channels[0]
                voice_client = await voice_channel.connect()
                self.sdr_up(voice_client)
                print('err')

            if message.content.startswith('$sdr-down'):
                self.sdr_down()
                await voice_client.disconnect()
                print('here')

        client.run(self.client_id)

    def sdr_up(self, vc):
        self.que = queue.Queue()

        self._init_sdr()
        self.sdr_thread = threading.Thread(target=self.play_sdr)
        self.sdr_thread.start()

        self.discord_thread = threading.Thread(target=self.stream_to_discord, args=(vc,))
        self.discord_thread.start()

    def _init_sdr(self):
        Fs = 2.048e6
        tune = 104.8e6
        gain = 30

        self.sdr = rtlsdr.RtlSdr(0)
        self.sdr.set_sample_rate(Fs)
        self.sdr.set_manual_gain_enabled(1)
        self.sdr.set_gain(gain)
        self.sdr.set_center_freq(tune)

    def play_sdr(self):

        length = 1024 * 50
        self.sdr.read_samples_async(self.capture_callback, length)

    def stream_to_discord(self, vc, target_rate=48000):
        fs = int(self.sdr.get_sample_rate() / 50)
        opus_encoder = opuslib.classes.Encoder(target_rate, 1, 'audio')

        duration_s = 0.02
        duration_len = int(duration_s * fs)

        _start = time.perf_counter()
        _loops = 0
        DELAY = duration_s
        chunk = None

        while True:
            data = self.que.get()
            data = dsp_utils.fm_de_mod(data)
            data = np.int32(data / np.max(np.abs(data)) * 2147483647)
            if chunk is not None:
                data = np.insert(data, 1, chunk)
            chunks_len = math.ceil(len(data)/duration_len)

            for i in range(chunks_len):
                start = i*duration_len
                end = min((i+1)*duration_len, len(data))
                chunk = data[start:end]
                if len(chunk) != duration_len:
                    break

                number_of_samples = round(len(chunk) * float(target_rate) / fs)
                wav_bytes_resampled = signal.resample(chunk, number_of_samples)
                wav_bytes_resampled = wav_bytes_resampled.astype(int)

                buf = dsp_utils.int32_to_pcm16(wav_bytes_resampled)
                encoded = opus_encoder.encode(buf, 960)
                _loops += 1

                vc.send_audio_packet(encoded, encode=False)
                next_time = _start + DELAY * _loops
                delay = max(0, DELAY + (next_time - time.perf_counter()))
                time.sleep(delay)

                chunk = None

                # buf = float_to_pcm16(data)

    def sdr_down(self):
        if self.sdr_thread is not None:
            self.sdr_thread.join()

        self.sdr.close()

        if self.discord_thread is not None:
            self.discord_thread.join()

    def capture_callback(self, capture, rtlsdr_obj):
        self.que.put(capture)

