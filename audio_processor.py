"""
Simple audio processing utilities for RoboSampla.
Handles silence removal, normalization, quiet start removal, and fades.
"""
import os
import glob
from pydub import AudioSegment
import numpy as np
from scipy import signal


def remove_silence(audio_segment: AudioSegment, silence_threshold_db: float = -55.0, min_silence_ms: float = 500.0) -> AudioSegment:
    """
    Remove silence from the beginning and end of audio using adaptive silence detection.
    
    Steps:
    1. Remove last 50ms (recording artifacts)
    2. Analyze last 500ms to determine silence threshold
    3. Remove silence from beginning and end based on this threshold
    
    Args:
        audio_segment: AudioSegment object
        silence_threshold_db: Fallback threshold in dB (not used in adaptive mode)
        min_silence_ms: Minimum silence duration to detect for trimming (milliseconds)
    
    Returns:
        Trimmed AudioSegment
    """
    if len(audio_segment) == 0:
        return audio_segment
    
    # Step 1: Remove last 50ms to eliminate recording artifacts/noises
    if len(audio_segment) > 50:
        audio_segment = audio_segment[:-50]
    
    if len(audio_segment) == 0:
        return audio_segment
    
    # Step 2: Get the max peak in last 500ms of sample to use as silence threshold
    tail_analysis_ms = min(500, len(audio_segment))  # Don't exceed sample length
    tail_segment = audio_segment[-tail_analysis_ms:]
    
    # Get the peak level in the tail - this represents our "silence" level
    tail_peak_db = tail_segment.max_dBFS
    
    # If tail is completely silent, use the provided threshold
    if tail_peak_db == -float('inf'):
        silence_threshold_db_actual = silence_threshold_db
    else:
        # Use the tail peak as our silence threshold (maybe add small margin)
        silence_threshold_db_actual = tail_peak_db + 3.0  # 3dB margin above tail noise
    
    # Step 3: Remove silence from beginning and end using this adaptive threshold
    # Convert to numpy array for analysis
    samples = np.array(audio_segment.get_array_of_samples())
    
    # Handle stereo by taking max of both channels
    if audio_segment.channels == 2:
        samples = samples.reshape((-1, 2))
        samples_mono = np.max(np.abs(samples), axis=1)
    else:
        samples_mono = np.abs(samples)
    
    # Convert threshold from dB to linear amplitude
    max_amplitude = 32767.0 if audio_segment.sample_width == 2 else 2147483647.0
    threshold_linear = max_amplitude * (10 ** (silence_threshold_db_actual / 20))
    
    # Find non-silent samples
    above_threshold = samples_mono > threshold_linear
    
    if not np.any(above_threshold):
        return audio_segment  # No samples above threshold, return as-is
    
    # Find first and last non-silent samples
    non_silent_indices = np.where(above_threshold)[0]
    first_sound = non_silent_indices[0]
    last_sound = non_silent_indices[-1]
    
    # Convert to milliseconds
    start_ms = int(first_sound * 1000 / audio_segment.frame_rate)
    end_ms = int((last_sound + 1) * 1000 / audio_segment.frame_rate)  # +1 to include the last sample
    
    return audio_segment[start_ms:end_ms]


def normalize_peak(audio_segment: AudioSegment, target_peak_db: float = -6.0) -> AudioSegment:
    """
    Normalize audio to target peak level.
    
    Args:
        audio_segment: AudioSegment object
        target_peak_db: Target peak level in dB
    
    Returns:
        Normalized AudioSegment
    """
    current_peak_db = audio_segment.max_dBFS
    
    if current_peak_db == -float('inf'):
        return audio_segment  # Silent audio
    
    # Calculate gain needed
    gain_db = target_peak_db - current_peak_db
    
    # Apply gain
    return audio_segment + gain_db


def remove_quiet_start(audio_segment: AudioSegment, quiet_threshold_db: float = -5.0) -> AudioSegment:
    """
    Remove quiet parts from the beginning until we reach the threshold level.
    
    Args:
        audio_segment: AudioSegment object
        quiet_threshold_db: Minimum dB level for sample start
    
    Returns:
        AudioSegment with quiet start removed
    """
    if len(audio_segment) == 0:
        return audio_segment
    
    # Convert to numpy array for analysis
    samples = np.array(audio_segment.get_array_of_samples())
    
    # Handle stereo by taking max of both channels
    if audio_segment.channels == 2:
        samples = samples.reshape((-1, 2))
        samples_mono = np.max(np.abs(samples), axis=1)
    else:
        samples_mono = np.abs(samples)
    
    # Convert threshold from dB to linear amplitude
    max_amplitude = 32767.0 if audio_segment.sample_width == 2 else 2147483647.0
    threshold_linear = max_amplitude * (10 ** (quiet_threshold_db / 20))
    
    # Find first sample above threshold
    above_threshold = samples_mono > threshold_linear
    
    if not np.any(above_threshold):
        return audio_segment  # No samples above threshold, return as-is
    
    # Find first sample above threshold
    first_loud_sample = np.where(above_threshold)[0][0]
    
    # Convert to milliseconds
    start_ms = int(first_loud_sample * 1000 / audio_segment.frame_rate)
    
    return audio_segment[start_ms:]


def apply_fade(audio_segment: AudioSegment, fade_in_ms: float = 5.0, fade_out_ms: float = 5.0) -> AudioSegment:
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
    
    # Don't fade if the audio is shorter than the fade duration
    fade_in_ms = min(fade_in_ms, len(audio_segment) / 2)
    fade_out_ms = min(fade_out_ms, len(audio_segment) / 2)
    
    result = audio_segment
    
    if fade_in_ms > 0:
        result = result.fade_in(int(fade_in_ms))
    
    if fade_out_ms > 0:
        result = result.fade_out(int(fade_out_ms))
    
    return result


def analyze_sample(audio_segment: AudioSegment, filename: str) -> dict:
    """
    Analyze audio sample for quality metrics and characteristics.
    
    Args:
        audio_segment: AudioSegment object
        filename: Name of the file for reporting
    
    Returns:
        Dictionary with analysis results
    """
    if len(audio_segment) == 0:
        return {"filename": filename, "length_ms": 0, "issues": ["Empty file"]}
    
    # Convert to numpy array for analysis
    samples = np.array(audio_segment.get_array_of_samples())
    
    # Handle stereo by taking max of both channels for analysis
    if audio_segment.channels == 2:
        samples = samples.reshape((-1, 2))
        samples_mono = np.max(np.abs(samples), axis=1)
        samples_for_dc = np.mean(samples, axis=1)  # Use mean for DC offset check
    else:
        samples_mono = np.abs(samples)
        samples_for_dc = samples
    
    # Calculate maximum possible value for this bit depth
    max_val = 32767 if audio_segment.sample_width == 2 else 2147483647
    
    issues = []
    
    # 1. Clipping detection
    clipped_samples = np.sum(samples_mono >= max_val * 0.99)  # 99% of max to catch near-clipping
    clipping_percentage = (clipped_samples / len(samples_mono)) * 100
    if clipping_percentage > 0.1:  # More than 0.1% clipped samples
        issues.append(f"Clipping: {clipping_percentage:.1f}% samples")
    
    # 2. DC offset detection
    dc_offset = np.mean(samples_for_dc)
    dc_offset_db = 20 * np.log10(abs(dc_offset) / max_val) if dc_offset != 0 else -120
    if dc_offset_db > -60:  # Significant DC offset
        issues.append(f"DC offset: {dc_offset_db:.1f}dB")
    
    return {
        "filename": filename,
        "length_ms": len(audio_segment),
        "peak_db": audio_segment.max_dBFS,
        "clipping_pct": clipping_percentage,
        "dc_offset_db": dc_offset_db,
        "issues": issues
    }


def analyze_patch_consistency(analysis_results: list) -> dict:
    """
    Analyze patch for length consistency and overall quality.
    
    Args:
        analysis_results: List of individual sample analysis results
    
    Returns:
        Dictionary with patch-level analysis
    """
    if not analysis_results:
        return {"expected_length_ms": 0, "length_outliers": [], "quality_issues": 0}
    
    # Get all lengths (excluding empty files)
    lengths = [r["length_ms"] for r in analysis_results if r["length_ms"] > 0]
    
    if not lengths:
        return {"expected_length_ms": 0, "length_outliers": [], "quality_issues": 0}
    
    # Calculate expected length (median is more robust than mean for outliers)
    expected_length = int(np.median(lengths))
    
    # Find length outliers (samples that are significantly different)
    length_outliers = []
    tolerance_pct = 20  # 20% tolerance
    min_acceptable = expected_length * (1 - tolerance_pct / 100)
    max_acceptable = expected_length * (1 + tolerance_pct / 100)
    
    for result in analysis_results:
        length = result["length_ms"]
        if length > 0 and (length < min_acceptable or length > max_acceptable):
            deviation_pct = ((length - expected_length) / expected_length) * 100
            length_outliers.append({
                "filename": result["filename"],
                "length_ms": length,
                "deviation_pct": deviation_pct
            })
    
    # Count total quality issues
    quality_issues = sum(1 for r in analysis_results if r["issues"])
    
    return {
        "expected_length_ms": expected_length,
        "length_outliers": length_outliers,
        "quality_issues": quality_issues,
        "total_samples": len(analysis_results)
    }


def process_sample(input_file: str, output_file: str = None,
                  silence_threshold_db: float = -55.0,
                  target_peak_db: float = -1.0,
                  quiet_start_threshold_db: float = -5.0,
                  fade_in_ms: float = 5.0,
                  fade_out_ms: float = 5.0,
                  min_silence_ms: float = 500.0) -> bool:
    """
    Process a single audio sample through the complete chain.
    
    Processing chain:
    1. Remove silence from beginning and end (includes 50ms end removal)
    2. Normalize to target peak level
    3. Remove quiet parts from beginning (until threshold)
    4. Apply fade in/out
    5. Analyze sample quality
    
    Args:
        input_file: Path to input WAV file
        output_file: Path to output WAV file (overwrites input if None)
        silence_threshold_db: Silence detection threshold
        target_peak_db: Target peak level for normalization
        quiet_start_threshold_db: Minimum level for sample start
        fade_in_ms: Fade in duration
        fade_out_ms: Fade out duration
        min_silence_ms: Minimum silence duration to detect for trimming
    
    Returns:
        Tuple of (success, analysis_result)
    """
    try:
        # Load audio
        audio = AudioSegment.from_wav(input_file)
        
        if len(audio) == 0:
            print(f"  {os.path.basename(input_file)}: Empty file, skipping")
            return False
        
        original_length = len(audio)
        original_bit_depth = audio.sample_width * 8
        
        # Step 1: Remove silence from beginning and end (includes 50ms end removal)
        audio = remove_silence(audio, silence_threshold_db, min_silence_ms)
        if len(audio) == 0:
            print(f"  {os.path.basename(input_file)}: All silence, skipping")
            return False
        length_after_silence = len(audio)
        
        # Step 2: Normalize to target peak
        audio = normalize_peak(audio, target_peak_db)
        
        # Step 3: Remove quiet start (after normalization)
        audio = remove_quiet_start(audio, quiet_start_threshold_db)
        if len(audio) == 0:
            print(f"  {os.path.basename(input_file)}: No loud content, skipping")
            return False
        length_after_quiet_removal = len(audio)
        
        # Step 4: Apply fades
        audio = apply_fade(audio, fade_in_ms, fade_out_ms)
        
        # Save result
        output_path = output_file if output_file else input_file
        audio.export(output_path, format="wav")
        
        # Step 5: Analyze sample quality
        filename = os.path.basename(input_file)
        analysis = analyze_sample(audio, filename)
        
        # Report processing
        final_length = len(audio)
        final_peak = audio.max_dBFS
        
        # Calculate silence removed
        silence_removed_ms = original_length - length_after_silence
        quiet_start_removed_ms = length_after_silence - length_after_quiet_removal
        total_removed_ms = silence_removed_ms + quiet_start_removed_ms
        total_removed_sec = total_removed_ms / 1000.0
        
        bit_depth_info = f" ({original_bit_depth}-bit)" if original_bit_depth != 16 else ""
        silence_info = f", removed {total_removed_sec:.1f}s silence" if total_removed_ms > 0 else ""
        issues_info = f" ⚠️ {', '.join(analysis['issues'])}" if analysis['issues'] else ""
        #print(f"  {filename}: {original_length}ms -> {final_length}ms, peak: {final_peak:.1f}dB{bit_depth_info}{silence_info}{issues_info}")
        
        return True, analysis
        
    except Exception as e:
        filename = os.path.basename(input_file)
        print(f"  Error processing {filename}: {e}")
        return False, {
            "filename": filename,
            "length_ms": 0,
            "peak_db": -float('inf'),
            "clipping_pct": 0,
            "dc_offset_db": -120,
            "issues": [f"Processing failed: {e}"]
        }


def process_patch_folder(patch_folder: str,
                        silence_threshold_db: float = -55.0,
                        target_peak_db: float = -6.0,
                        quiet_start_threshold_db: float = -5.0,
                        fade_in_ms: float = 5.0,
                        fade_out_ms: float = 5.0,
                        min_silence_ms: float = 500.0) -> tuple[bool, list]:
    """
    Process all WAV files in a patch folder.
    
    Args:
        patch_folder: Path to folder containing WAV files
        silence_threshold_db: Silence detection threshold
        target_peak_db: Target peak level for normalization
        quiet_start_threshold_db: Minimum level for sample start
        fade_in_ms: Fade in duration
        fade_out_ms: Fade out duration
        min_silence_ms: Minimum silence duration to detect for trimming
    
    Returns:
        Tuple of (success, list_of_errors)
    """
    print(f"Processing patch folder: {os.path.basename(patch_folder)}")
    
    # Find all WAV files
    wav_files = glob.glob(os.path.join(patch_folder, "*.wav"))
    
    if not wav_files:
        print("No WAV files found")
        return False, [{"filename": "folder", "description": "No WAV files found"}]
    
    # Sort by numeric prefix if present, then alphabetically
    def sort_key(filepath):
        filename = os.path.basename(filepath)
        # Try to extract numeric prefix
        import re
        match = re.match(r'^(\d+)', filename)
        if match:
            return (int(match.group(1)), filename)
        else:
            return (float('inf'), filename)  # Files without numeric prefix go last
    
    wav_files.sort(key=sort_key)
    print(f"Found {len(wav_files)} samples for processing")
    
    success_count = 0
    errors = []
    analysis_results = []
    
    for wav_file in wav_files:
        success, analysis = process_sample(
            input_file=wav_file,
            silence_threshold_db=silence_threshold_db,
            target_peak_db=target_peak_db,
            quiet_start_threshold_db=quiet_start_threshold_db,
            fade_in_ms=fade_in_ms,
            fade_out_ms=fade_out_ms,
            min_silence_ms=min_silence_ms
        )
        
        analysis_results.append(analysis)
        
        if success:
            success_count += 1
        else:
            errors.append({
                "filename": os.path.basename(wav_file),
                "description": "Processing failed"
            })
    
    # Analyze patch consistency
    patch_analysis = analyze_patch_consistency(analysis_results)
    
    # Report patch analysis
    print(f"\n📊 PATCH ANALYSIS:")
    print(f"  Expected sample length: {patch_analysis['expected_length_ms']}ms")
    
    if patch_analysis['length_outliers']:
        print(f"  ⚠️ Length outliers ({len(patch_analysis['length_outliers'])}):")
        for outlier in patch_analysis['length_outliers'][:5]:  # Show first 5
            print(f"    {outlier['filename']}: {outlier['length_ms']}ms ({outlier['deviation_pct']:+.0f}%)")
        if len(patch_analysis['length_outliers']) > 5:
            print(f"    ... and {len(patch_analysis['length_outliers']) - 5} more")
    
    if patch_analysis['quality_issues'] > 0:
        print(f"  ⚠️ Quality issues found in {patch_analysis['quality_issues']} samples:")
        for result in analysis_results:
            if result['issues']:
                print(f"    {result['filename']}: {', '.join(result['issues'])}")
    else:
        print(f"  ✅ No quality issues detected")
    
    print(f"Processed {success_count}/{len(wav_files)} samples successfully")
    
    return success_count > 0, errors
