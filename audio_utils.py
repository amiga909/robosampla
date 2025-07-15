"""
Audio recording utilities using sounddevice.
"""
import sounddevice as sd
import scipy.io.wavfile as wav
import numpy as np
import os


def list_audio_devices():
    """List all available audio input and output devices."""
    print("Available Audio Devices:")
    print("-" * 50)
    devices = sd.query_devices()
    for i, device in enumerate(devices):
        device_type = []
        max_inputs = device.get('max_inputs', 0)
        max_outputs = device.get('max_outputs', 0)
        
        if max_inputs > 0:
            device_type.append('INPUT')
        if max_outputs > 0:
            device_type.append('OUTPUT')
        
        device_name = device.get('name', 'Unknown Device')
        default_samplerate = device.get('default_samplerate', 0)
        
        print(f"Device {i}: {device_name}")
        print(f"  Type: {'/'.join(device_type) if device_type else 'Unknown'}")
        print(f"  Channels: In={max_inputs}, Out={max_outputs}")
        print(f"  Sample Rate: {default_samplerate:.0f} Hz")
        print()
    
    # Show default devices
    try:
        default_input = sd.default.device[0]
        default_output = sd.default.device[1]
        input_name = devices[default_input].get('name', 'Unknown') if default_input < len(devices) else 'Unknown'
        output_name = devices[default_output].get('name', 'Unknown') if default_output < len(devices) else 'Unknown'
        print(f"Default Input Device: {default_input} ({input_name})")
        print(f"Default Output Device: {default_output} ({output_name})")
    except Exception as e:
        print(f"Default devices: Not available ({e})")
    print()


def get_device_channels(device_id):
    """Get the number of input channels for a specific audio device."""
    try:
        device_info = sd.query_devices(device_id)
        max_input_channels = device_info.get('max_inputs', 1)
        return min(2, max_input_channels) if max_input_channels > 0 else 1
    except:
        return 1  # Fallback to mono


def record_audio(duration, sample_rate=44100, device=None, channels=None):
    """Record audio for the specified duration."""
    if channels is None:
        channels = get_device_channels(device) if device is not None else 1
    
    print(f"Recording audio for {duration:.2f} seconds... (channels: {channels})")
    recording = sd.rec(int(duration * sample_rate), 
                      samplerate=sample_rate, channels=channels, 
                      dtype='float64', device=device)
    sd.wait()  # Wait until recording is finished
    return recording


def save_audio(recording, filepath, sample_rate=44100):
    """Save audio recording to a WAV file."""
    # Convert to 16-bit and save
    # Handle both mono and stereo recordings
    if recording.ndim == 1:
        # Mono recording
        audio_int16 = (recording * 32767).astype(np.int16)
    else:
        # Stereo recording
        audio_int16 = (recording * 32767).astype(np.int16)
    
    wav.write(filepath, sample_rate, audio_int16)
    return recording.shape
