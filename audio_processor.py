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
                   min_silence_len: int = 5) -> tuple[AudioSegment, dict]:
    """
    Remove silence from the beginning and end of audio using amplitude-based detection.
    
    Args:
        audio_segment: AudioSegment object
        silence_threshold_db: Threshold in dB below which audio is considered silence
        min_silence_len: Minimum length of silence in milliseconds to consider
    
    Returns:
        Tuple of (trimmed AudioSegment, error_info dict)
    """
    original_length = len(audio_segment)
    error_info = {"has_error": False, "error_type": None, "description": None}
    
    if original_length == 0:
        return audio_segment, error_info
    
    # Convert to numpy array for analysis
    samples = np.array(audio_segment.get_array_of_samples())
    
    # Handle stereo by taking max of both channels
    if audio_segment.channels == 2:
        samples = samples.reshape((-1, 2))
        # Use RMS of both channels for better detection, but handle potential negative values
        samples_squared = samples.astype(np.float64) ** 2  # Convert to float64 to avoid overflow
        samples_mono = np.sqrt(np.mean(samples_squared, axis=1))
    else:
        samples_mono = np.abs(samples.astype(np.float64))
    
    # Convert threshold from dB to linear amplitude
    # For 16-bit audio, full scale is 32767
    max_amplitude = 32767.0 if audio_segment.sample_width == 2 else 2147483647.0
    threshold_linear = max_amplitude * (10 ** (silence_threshold_db / 20))
    
    # print(f"Detecting silence with threshold {silence_threshold_db} dB (linear: {threshold_linear:.0f})")
    
    # Find samples above threshold
    above_threshold = samples_mono > threshold_linear
    
    sample_rate = audio_segment.frame_rate
    
    # Find first and last samples above threshold for simple trimming
    above_indices = np.where(above_threshold)[0]
    
    if len(above_indices) == 0:
        print(f"  No audio above threshold detected, keeping original length ({original_length} ms)")
        error_info = {
            "has_error": True, 
            "error_type": "no_audio", 
            "description": f"No audio above {silence_threshold_db} dB threshold detected"
        }
        return audio_segment, error_info
    
    # Simple approach: find first and last samples above threshold
    first_audio_sample = above_indices[0]
    last_audio_sample = above_indices[-1]
    
    # Be very aggressive at the beginning - find where audio has reasonable amplitude
    # Search forward from first detection to find a much stronger signal
    search_window = int(200 * sample_rate / 1000)  # Search 200ms forward for better detection
    search_end = min(first_audio_sample + search_window, len(samples_mono))
    
    # Use much higher threshold for start detection (very aggressive trimming)
    # This ensures audio starts with reasonable amplitude, not just barely audible
    attack_threshold = threshold_linear * 10  # 10x the threshold for meaningful audio start
    
    start_sample = first_audio_sample
    if search_end > first_audio_sample:
        search_region = samples_mono[first_audio_sample:search_end]
        attack_indices = np.where(search_region > attack_threshold)[0]
        
        if len(attack_indices) > 0:
            # Use the first strong attack as the start point
            start_sample = first_audio_sample + attack_indices[0]
            #print(f"  Found meaningful audio start at sample {start_sample} (was {first_audio_sample})")
        else:
            # If no strong attack found, use a medium threshold as fallback
            medium_threshold = threshold_linear * 5  # 5x threshold as fallback
            medium_indices = np.where(search_region > medium_threshold)[0]
            if len(medium_indices) > 0:
                start_sample = first_audio_sample + medium_indices[0]
               #print(f"  Found medium audio start at sample {start_sample} (fallback from {first_audio_sample})")
    
    # For the end, just use the last sample above threshold
    end_sample = last_audio_sample
    
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
    
    #print(f"  Silence detected: {silence_start} ms at start, {silence_end} ms at end")
    #print(f"  Silence removed: {removed_start} ms at start, {removed_end} ms at end")
    #print(f"  Length: {original_length} ms -> {end_time - start_time} ms")
    
    return audio_segment[start_time:end_time], error_info


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
                   fade_in_ms: float = 1.0, fade_out_ms: float = 1.0) -> tuple[AudioSegment, dict]:
    """
    Process a single audio sample: remove silence and apply fades.
    
    Args:
        audio_segment: AudioSegment object
        silence_threshold_db: Threshold for silence detection
        fade_in_ms: Fade in duration in milliseconds
        fade_out_ms: Fade out duration in milliseconds
    
    Returns:
        Tuple of (processed AudioSegment, error_info dict)
    """
    # Remove silence from beginning and end
    trimmed, error_info = remove_silence(audio_segment, silence_threshold_db)
    
    # Apply fades to the trimmed audio
    faded = apply_fade(trimmed, fade_in_ms, fade_out_ms)
    
    return faded, error_info


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


def normalize_patch_hybrid(patch_folder: str, target_peak_db: float = -6.0,
                          fade_in_ms: float = 1.0, fade_out_ms: float = 1.0) -> None:
    """
    Hybrid normalization: Preserves some relative dynamics while ensuring consistency.
    Uses 20% relative dynamics + 80% individual normalization for best of both worlds.
    
    Args:
        patch_folder: Path to folder containing WAV files
        target_peak_db: Target peak level in dB
        fade_in_ms: Fade in duration in milliseconds
        fade_out_ms: Fade out duration in milliseconds
    """
    print(f"Normalizing patch (hybrid): {os.path.basename(patch_folder)}")
    
    # Analyze all levels first
    levels = analyze_patch_levels(patch_folder)
    
    if not levels:
        print("No WAV files found in patch folder")
        return
    
    # Find the maximum level across all samples
    max_level_db = max(levels.values())
    loudest_file = max(levels, key=levels.get)
    
    if max_level_db == -float('inf'):
        print("Warning: All samples are silent")
        return
    
    # Analyze level consistency - check for outliers
    level_values = list(levels.values())
    level_values.sort(reverse=True)  # Sort from loudest to quietest
    
    if len(level_values) >= 3:
        # Calculate statistics
        median_level = level_values[len(level_values) // 2]
        loudest_level = level_values[0]
        loudest_vs_median = loudest_level - median_level
        
        # Check if only a few samples are much louder than the rest
        samples_near_loudest = sum(1 for level in level_values if level >= loudest_level - 6.0)
        total_samples = len(level_values)
        
        # Warn if only 1-2 samples are much louder than the rest
        if samples_near_loudest <= 2 and total_samples >= 5 and loudest_vs_median > 12.0:
            outlier_files = [filename for filename, level in levels.items() 
                           if level >= loudest_level - 3.0]
            print(f"⚠️  Warning: Level inconsistency detected!")
            print(f"    Only {samples_near_loudest}/{total_samples} samples are loud (within 6dB of peak)")
            print(f"    Loudest sample is {loudest_vs_median:.1f} dB above median")
            print(f"    Outlier file(s): {', '.join(outlier_files)}")
            print(f"    Hybrid normalization will reduce these inconsistencies")
    
    print(f"Max level found: {max_level_db:.1f} dB (in {loudest_file})")
    print(f"Target level: {target_peak_db:.1f} dB")
    
    # Calculate hybrid normalization for each sample
    wav_files = glob.glob(os.path.join(patch_folder, "*.wav"))
    wav_files.sort()
    
    for wav_file in wav_files:
        try:
            audio = AudioSegment.from_wav(wav_file)
            filename = os.path.basename(wav_file)
            
            current_peak_db = levels[filename]
            
            if current_peak_db == -float('inf'):
                print(f"  {filename}: Silent sample, skipping")
                continue
            
            # Hybrid approach:
            # 1. Calculate relative boost (preserves some dynamics)
            relative_boost = target_peak_db - max_level_db
            
            # 2. Calculate individual boost (ensures consistency) 
            individual_boost = target_peak_db - current_peak_db
            
            # 3. Combine: 20% relative + 80% individual
            # This preserves some musical dynamics while ensuring good consistency
            hybrid_boost = (0.2 * relative_boost) + (0.8 * individual_boost)
            
            # Ensure we don't boost beyond reasonable limits
            if hybrid_boost > 20:
                #print(f"  {filename}: Boost amount ({hybrid_boost:.1f} dB) is very high, limiting to 20 dB")
                hybrid_boost = 20
            
            # Convert dB boost to linear gain factor
            gain_factor = 10 ** (hybrid_boost / 20)
            
            # Get raw audio data as numpy array
            samples = np.array(audio.get_array_of_samples())
            
            # Handle stereo
            if audio.channels == 2:
                samples = samples.reshape((-1, 2))
            
            # Apply gain factor
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
            
            new_peak = current_peak_db + hybrid_boost
            #print(f"  {filename}: {current_peak_db:.1f} dB -> {new_peak:.1f} dB (boost: {hybrid_boost:+.1f} dB)")
            
        except Exception as e:
            print(f"Error normalizing {wav_file}: {e}")


def process_recorded_sample(filepath: str, sample_rate: int, 
                           silence_threshold_db: float = -40.0,
                           fade_in_ms: float = 1.0, fade_out_ms: float = 1.0) -> tuple[bool, dict]:
    """
    Process a single recorded audio file: remove silence and apply fades.
    
    Args:
        filepath: Path to the WAV file
        sample_rate: Sample rate in Hz (not used with pydub, but kept for compatibility)
        silence_threshold_db: Threshold for silence detection
        fade_in_ms: Fade in duration in milliseconds
        fade_out_ms: Fade out duration in milliseconds
    
    Returns:
        Tuple of (success bool, error_info dict)
    """
    try:
        # Load the audio file
        audio = AudioSegment.from_wav(filepath)
        
        # Process the sample
        processed, error_info = process_sample(audio, silence_threshold_db, fade_in_ms, fade_out_ms)
        
        # Save the processed file
        processed.export(filepath, format="wav")
        
        return True, error_info
        
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        error_info = {
            "has_error": True,
            "error_type": "processing_error", 
            "description": f"Error processing file: {e}"
        }
        return False, error_info


def process_patch_folder(patch_folder: str, sample_rate: int, 
                        target_peak_db: float = -6.0,
                        fade_in_ms: float = 1.0, fade_out_ms: float = 1.0,
                        silence_threshold_db: float = -55.0) -> tuple[bool, list]:
    """
    Process all samples in a patch folder and then normalize them using hybrid approach.
    
    Args:
        patch_folder: Path to folder containing WAV files
        sample_rate: Sample rate in Hz
        target_peak_db: Target peak level in dB
        fade_in_ms: Fade in duration in milliseconds
        fade_out_ms: Fade out duration in milliseconds
        silence_threshold_db: Threshold for silence detection
    
    Returns:
        Tuple of (success bool, list of error_info dicts)
    """
    print(f"Processing patch folder: {os.path.basename(patch_folder)}")
    
    # Get all WAV files
    wav_files = glob.glob(os.path.join(patch_folder, "*.wav"))
    wav_files.sort()  # Sort by filename for consistent processing order
    
    if not wav_files:
        print("No WAV files found in patch folder")
        return False, []
    
    print(f"Found {len(wav_files)} samples for processing")
    
    # Collect errors from processing
    processing_errors = []
    
    # First, process each sample individually (silence removal + fades)
    for wav_file in wav_files:
        filename = os.path.basename(wav_file)
        #print(f"  Processing {filename}...")
        
        try:
            # Load the audio file
            audio = AudioSegment.from_wav(wav_file)
            
            # Process the sample (silence removal + fades)
            processed, error_info = process_sample(audio, silence_threshold_db, fade_in_ms, fade_out_ms)
            
            # Collect error info if there are issues
            if error_info["has_error"]:
                error_info["filename"] = filename
                processing_errors.append(error_info)
                print(f"    Warning: {error_info['description']}")
            
            # Save the processed file
            processed.export(wav_file, format="wav")
            
        except Exception as e:
            print(f"    Error processing {filename}: {e}")
            processing_errors.append({
                "filename": filename,
                "has_error": True,
                "error_type": "processing_error",
                "description": f"Error processing file: {e}"
            })
            return False, processing_errors
    
    # Then normalize all samples using hybrid approach
    normalize_patch_hybrid(patch_folder, target_peak_db, fade_in_ms, fade_out_ms)
    
    return True, processing_errors
