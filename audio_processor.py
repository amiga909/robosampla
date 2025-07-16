"""
Audio processing utilities for RoboSampla.
Handles silence removal, fade in/out, and patch-wise normalization.
"""
import os
import glob
from typing import Dict
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import numpy as np


def remove_silence(audio_segment: AudioSegment, 
                   silence_threshold_db: float = -40.0,
                   min_silence_len: int = 5) -> AudioSegment:
    """
    Remove silence from the beginning and end of audio using amplitude-based detection.
    Similar to SOX silence detection but adapted for individual samples.
    
    Args:
        audio_segment: AudioSegment object
        silence_threshold_db: Threshold in dB below which audio is considered silence
        min_silence_len: Minimum length of silence in milliseconds to consider
    
    Returns:
        Trimmed AudioSegment
    """
    original_length = len(audio_segment)
    
    if original_length == 0:
        return audio_segment
    
    # Convert to numpy array for analysis
    samples = np.array(audio_segment.get_array_of_samples())
    
    # Handle stereo by taking max of both channels
    if audio_segment.channels == 2:
        samples = samples.reshape((-1, 2))
        # Use RMS of both channels for better detection
        samples_mono = np.sqrt(np.mean(samples**2, axis=1))
    else:
        samples_mono = np.abs(samples)
    
    # Convert threshold from dB to linear amplitude
    # For 16-bit audio, full scale is 32767
    max_amplitude = 32767.0 if audio_segment.sample_width == 2 else 2147483647.0
    threshold_linear = max_amplitude * (10 ** (silence_threshold_db / 20))
    
    print(f"Detecting silence with threshold {silence_threshold_db} dB (linear: {threshold_linear:.0f})")
    
    # Find samples above threshold
    above_threshold = samples_mono > threshold_linear
    
    # Convert min_silence_len from ms to samples
    sample_rate = audio_segment.frame_rate
    min_silence_samples = int(min_silence_len * sample_rate / 1000)
    
    # Find first and last significant audio
    nonzero_indices = np.where(above_threshold)[0]
    
    if len(nonzero_indices) == 0:
        print(f"  No audio above threshold detected, keeping original length ({original_length} ms)")
        return audio_segment
    
    # Find start: first sample above threshold
    start_sample = nonzero_indices[0]
    
    # Find end: last sample above threshold  
    end_sample = nonzero_indices[-1]
    
    # Convert back to milliseconds
    start_time = int(start_sample * 1000 / sample_rate)
    end_time = int(end_sample * 1000 / sample_rate)
    
    # Calculate silence amounts
    silence_start = start_time
    silence_end = original_length - end_time
    
    # Add small buffer to avoid cutting too aggressively
    buffer_ms = 10  # Slightly larger buffer for safety
    start_time = max(0, start_time - buffer_ms)
    end_time = min(original_length, end_time + buffer_ms)
    
    # Calculate actual amounts removed after buffer
    removed_start = start_time
    removed_end = original_length - end_time
    
    print(f"  Silence detected: {silence_start} ms at start, {silence_end} ms at end")
    print(f"  Silence removed: {removed_start} ms at start, {removed_end} ms at end (with {buffer_ms} ms buffer)")
    print(f"  Length: {original_length} ms -> {end_time - start_time} ms")
    
    return audio_segment[start_time:end_time]


def apply_fade(audio_segment: AudioSegment, 
               fade_in_ms: float = 1.0, fade_out_ms: float = 1.0) -> AudioSegment:
    """
    Apply fade in and fade out to audio.
    
    Args:
        audio_segment: AudioSegment object
        fade_in_ms: Fade in duration in milliseconds
        fade_out_ms: Fade out duration in milliseconds
    
    Returns:
        AudioSegment with fades applied
    """
    if len(audio_segment) == 0:
        return audio_segment
    
    # Convert to integers (pydub works with milliseconds as integers)
    fade_in_ms = int(fade_in_ms)
    fade_out_ms = int(fade_out_ms)
    
    # Ensure fade lengths don't exceed audio length
    max_fade = len(audio_segment) // 4
    fade_in_ms = min(fade_in_ms, max_fade)
    fade_out_ms = min(fade_out_ms, max_fade)
    
    result = audio_segment
    
    if fade_in_ms > 0:
        result = result.fade_in(fade_in_ms)
    
    if fade_out_ms > 0:
        result = result.fade_out(fade_out_ms)
    
    return result


def process_sample(audio_segment: AudioSegment, 
                   silence_threshold_db: float = -40.0,
                   fade_in_ms: float = 1.0, fade_out_ms: float = 1.0) -> AudioSegment:
    """
    Process a single audio sample: remove silence and apply fades.
    
    Args:
        audio_segment: AudioSegment object
        silence_threshold_db: Threshold for silence detection
        fade_in_ms: Fade in duration in milliseconds
        fade_out_ms: Fade out duration in milliseconds
    
    Returns:
        Processed AudioSegment
    """
    # Remove silence from beginning and end
    trimmed = remove_silence(audio_segment, silence_threshold_db)
    
    return trimmed


def analyze_patch_levels(patch_folder: str) -> Dict[str, float]:
    """
    Analyze the peak levels of all WAV files in a patch folder.
    
    Args:
        patch_folder: Path to folder containing WAV files
    
    Returns:
        Dictionary mapping filename to peak level (in dB)
    """
    levels = {}
    wav_files = glob.glob(os.path.join(patch_folder, "*.wav"))
    wav_files.sort()  # Sort by filename for consistent processing order
    
    for wav_file in wav_files:
        try:
            audio = AudioSegment.from_wav(wav_file)
            
            # Calculate peak level (dBFS - decibels relative to full scale)
            peak_db = audio.max_dBFS
            levels[os.path.basename(wav_file)] = peak_db
            
        except Exception as e:
            print(f"Warning: Could not analyze {wav_file}: {e}")
            levels[os.path.basename(wav_file)] = -float('inf')
    
    return levels


def normalize_patch_relative(patch_folder: str, target_peak_db: float = -6.0,
                            fade_in_ms: float = 1.0, fade_out_ms: float = 1.0) -> None:
    """
    Normalize all WAV files in a patch folder relative to each other.
    The loudest sample will be normalized to target_peak_db, others scaled proportionally.
    
    Args:
        patch_folder: Path to folder containing WAV files
        target_peak_db: Target peak level in dB for the loudest sample
        fade_in_ms: Fade in duration in milliseconds
        fade_out_ms: Fade out duration in milliseconds
    """
    print(f"Normalizing patch: {os.path.basename(patch_folder)}")
    
    # Analyze all levels first
    levels = analyze_patch_levels(patch_folder)
    
    if not levels:
        print("No WAV files found in patch folder")
        return
    
    # Find the maximum level across all samples (least negative dB value)
    max_level_db = max(levels.values())
    
    if max_level_db == -float('inf'):
        print("Warning: All samples are silent")
        return
    
    # Calculate how much to boost to reach target
    boost_db = target_peak_db - max_level_db
    
    # Ensure we don't boost beyond reasonable limits to prevent clipping
    if boost_db > 20:
        print(f"Warning: Boost amount ({boost_db:.1f} dB) is very high, limiting to 20 dB")
        boost_db = 20
    
    print(f"Max level found: {max_level_db:.1f} dB")
    print(f"Boost to apply: {boost_db:.1f} dB")
    
    # Convert dB boost to linear gain factor
    gain_factor = 10 ** (boost_db / 20)
    
    # Apply normalization to all files
    wav_files = glob.glob(os.path.join(patch_folder, "*.wav"))
    wav_files.sort()  # Sort by filename for consistent processing order
    
    for wav_file in wav_files:
        try:
            audio = AudioSegment.from_wav(wav_file)
            
            # Get raw audio data as numpy array
            samples = np.array(audio.get_array_of_samples())
            
            # Handle stereo
            if audio.channels == 2:
                samples = samples.reshape((-1, 2))
            
            # Apply gain factor (safer than dB addition)
            samples_normalized = samples * gain_factor
            
            # Prevent clipping by limiting to int16 range
            max_val = 32767 if audio.sample_width == 2 else 2147483647
            samples_normalized = np.clip(samples_normalized, -max_val, max_val)
            
            # Convert back to AudioSegment
            if audio.channels == 2:
                samples_normalized = samples_normalized.flatten()
            
            normalized_audio = audio._spawn(samples_normalized.astype(samples.dtype).tobytes())
            # Apply fades
            faded = apply_fade(normalized_audio, fade_in_ms, fade_out_ms)
            # Export the normalized file
            faded.export(wav_file, format="wav")

            filename = os.path.basename(wav_file)
            original_peak = levels[filename]
            new_peak = original_peak + boost_db
            print(f"  {filename}: {original_peak:.1f} dB -> {new_peak:.1f} dB")
            
        except Exception as e:
            print(f"Error normalizing {wav_file}: {e}")


def process_recorded_sample(filepath: str, sample_rate: int, 
                           silence_threshold_db: float = -40.0,
                           fade_in_ms: float = 1.0, fade_out_ms: float = 1.0) -> bool:
    """
    Process a single recorded audio file: remove silence and apply fades.
    
    Args:
        filepath: Path to the WAV file
        sample_rate: Sample rate in Hz (not used with pydub, but kept for compatibility)
        silence_threshold_db: Threshold for silence detection
        fade_in_ms: Fade in duration in milliseconds
        fade_out_ms: Fade out duration in milliseconds
    
    Returns:
        True if processing was successful, False otherwise
    """
    try:
        # Load the audio file
        audio = AudioSegment.from_wav(filepath)
        
        # Process the sample
        processed = process_sample(audio, silence_threshold_db, fade_in_ms, fade_out_ms)
        
        # Save the processed file
        processed.export(filepath, format="wav")
        
        return True
        
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False


def process_patch_folder(patch_folder: str, sample_rate: int, 
                        target_peak_db: float = -6.0,
                        fade_in_ms: float = 1.0, fade_out_ms: float = 1.0) -> bool:
    """
    Process all samples in a patch folder and then normalize them relative to each other.
    
    Args:
        patch_folder: Path to folder containing WAV files
        sample_rate: Sample rate in Hz
        target_peak_db: Target peak level in dB for the loudest sample
        fade_in_ms: Fade in duration in milliseconds
        fade_out_ms: Fade out duration in milliseconds
    
    Returns:
        True if processing was successful, False otherwise
    """
    print(f"Processing patch folder: {os.path.basename(patch_folder)}")
    
    # Get all WAV files
    wav_files = glob.glob(os.path.join(patch_folder, "*.wav"))
    wav_files.sort()  # Sort by filename for consistent processing order
    
    if not wav_files:
        print("No WAV files found in patch folder")
        return False
    
    # Samples are already processed individually, just need to normalize
    print(f"Found {len(wav_files)} samples for normalization")
    
    # Normalize all samples in the patch relative to each other
    normalize_patch_relative(patch_folder, target_peak_db, fade_in_ms, fade_out_ms)
    return True
