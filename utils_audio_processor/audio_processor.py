"""
Simple audio processing utilities for RoboSampla.
Handles silence removal, normalization, quiet start removal, and fades.
"""
import os
import glob
from pydub import AudioSegment
import numpy as np
from scipy import signal


def remove_silence(audio_segment: AudioSegment, threshold_db: float = -30.0) -> AudioSegment:
    """
    Remove silence from the beginning and end of audio using a simple threshold.
    
    Args:
        audio_segment: AudioSegment object
        threshold_db: Threshold in dB - anything below this is considered silence
    
    Returns:
        Trimmed AudioSegment
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
    threshold_linear = max_amplitude * (10 ** (threshold_db / 20))
    
    # Find samples above threshold (not silence)
    above_threshold = samples_mono > threshold_linear
    
    if not np.any(above_threshold):
        return AudioSegment.empty()  # Return empty segment when all audio is below threshold
    
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


def remove_end_artifacts(audio_segment: AudioSegment, trim_end_ms: float = 100.0) -> AudioSegment:
    """
    Remove recording artifacts from the end of audio by trimming the last N milliseconds.
    
    Args:
        audio_segment: AudioSegment object
        trim_end_ms: Duration to trim from the end in milliseconds
    
    Returns:
        AudioSegment with end trimmed
    """
    if len(audio_segment) == 0:
        return audio_segment
    
    # Don't trim if the audio is shorter than the trim duration
    if len(audio_segment) <= trim_end_ms:
        return audio_segment
    
    # Trim the end
    end_time_ms = len(audio_segment) - trim_end_ms
    return audio_segment[:int(end_time_ms)]


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
                  silence_threshold_db: float = -30.0,
                  target_peak_db: float = -1.0,
                  fade_in_ms: float = 5.0,
                  fade_out_ms: float = 5.0,
                  trim_end_ms: float = 100.0) -> bool:
    """
    Process a single audio sample through the simplified chain.
    
    Processing chain:
    1. Remove recording artifacts from the end (last 100ms)
    2. Remove silence from beginning and end using one threshold
    3. Normalize to target peak level
    4. Apply fade in/out
    5. Analyze sample quality
    
    Args:
        input_file: Path to input WAV file
        output_file: Path to output WAV file (overwrites input if None)
        silence_threshold_db: Silence detection threshold (clearly audible level)
        target_peak_db: Target peak level for normalization
        fade_in_ms: Fade in duration
        fade_out_ms: Fade out duration
        trim_end_ms: Duration to trim from end to remove recording artifacts
    
    Returns:
        Tuple of (success, analysis_result)
    """
    try:
        # Load audio
        audio = AudioSegment.from_wav(input_file)
        
        if len(audio) == 0:
            print(f"  {os.path.basename(input_file)}: Empty file, skipping")
            return False, {
                "filename": os.path.basename(input_file),
                "length_ms": 0,
                "peak_db": -float('inf'),
                "clipping_pct": 0,
                "dc_offset_db": -120,
                "issues": ["Empty file"]
            }
        
        original_length = len(audio)
        original_bit_depth = audio.sample_width * 8
        
        # Step 1: Remove recording artifacts from the end (last 100ms)
        audio = remove_end_artifacts(audio, trim_end_ms)
        if len(audio) == 0:
            print(f"  {os.path.basename(input_file)}: Audio too short after trimming end, skipping")
            return False, {
                "filename": os.path.basename(input_file),
                "length_ms": 0,
                "peak_db": -float('inf'),
                "clipping_pct": 0,
                "dc_offset_db": -120,
                "issues": ["Audio too short after trimming end"]
            }
        
        # Step 2: Remove silence from beginning and end
        audio = remove_silence(audio, silence_threshold_db)
        if len(audio) == 0:
            print(f"  {os.path.basename(input_file)}: Sample too quiet (below {silence_threshold_db}dB threshold), skipping")
            return False, {
                "filename": os.path.basename(input_file),
                "length_ms": 0,
                "peak_db": -float('inf'),
                "clipping_pct": 0,
                "dc_offset_db": -120,
                "issues": ["Sample too quiet - below silence threshold"]
            }
        
        # Step 3: Normalize to target peak
        audio = normalize_peak(audio, target_peak_db)
        
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
        silence_removed_ms = original_length - final_length
        silence_removed_sec = silence_removed_ms / 1000.0
        
        bit_depth_info = f" ({original_bit_depth}-bit)" if original_bit_depth != 16 else ""
        silence_info = f", removed {silence_removed_sec:.1f}s silence" if silence_removed_ms > 0 else ""
        issues_info = f" ⚠️ {', '.join(analysis['issues'])}" if analysis['issues'] else ""
        
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
                        silence_threshold_db: float = -30.0,
                        target_peak_db: float = -6.0,
                        fade_in_ms: float = 5.0,
                        fade_out_ms: float = 5.0,
                        trim_end_ms: float = 100.0) -> tuple[bool, list]:
    """
    Process all WAV files in a patch folder.
    If any samples are too quiet, marks the folder as incomplete and omits quiet samples.
    
    Args:
        patch_folder: Path to folder containing WAV files
        silence_threshold_db: Silence detection threshold (clearly audible level)
        target_peak_db: Target peak level for normalization
        fade_in_ms: Fade in duration
        fade_out_ms: Fade out duration
        trim_end_ms: Duration to trim from end to remove recording artifacts
    
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
    quiet_samples = []
    
    for wav_file in wav_files:
        success, analysis = process_sample(
            input_file=wav_file,
            silence_threshold_db=silence_threshold_db,
            target_peak_db=target_peak_db,
            fade_in_ms=fade_in_ms,
            fade_out_ms=fade_out_ms,
            trim_end_ms=trim_end_ms
        )
        
        # Check if sample was too quiet
        if not success and any("too quiet" in issue.lower() for issue in analysis.get("issues", [])):
            quiet_samples.append(os.path.basename(wav_file))
            # Remove the quiet sample from output folder
            if os.path.exists(wav_file):
                os.remove(wav_file)
                print(f"  Removed quiet sample: {os.path.basename(wav_file)}")
        else:
            analysis_results.append(analysis)
            if success:
                success_count += 1
            else:
                errors.append({
                    "filename": os.path.basename(wav_file),
                    "description": "Processing failed"
                })
    
    # If any samples were too quiet, rename folder to indicate incomplete patch
    if quiet_samples:
        parent_dir = os.path.dirname(patch_folder)
        folder_name = os.path.basename(patch_folder)
        
        # Add _incomplete_ prefix if not already present
        if not folder_name.startswith("_incomplete_"):
            new_folder_name = f"_incomplete_{folder_name}"
            new_folder_path = os.path.join(parent_dir, new_folder_name)
            
            # Rename the folder
            try:
                os.rename(patch_folder, new_folder_path)
                print(f"📁 Renamed folder to: {new_folder_name}")
                print(f"⚠️  Removed {len(quiet_samples)} quiet samples: {', '.join(quiet_samples)}")
                patch_folder = new_folder_path  # Update path for analysis
            except OSError as e:
                print(f"⚠️  Could not rename folder: {e}")
    
    # Only analyze patch consistency for successfully processed samples
    if analysis_results:
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
    
    total_processed = success_count
    if quiet_samples:
        print(f"Processed {total_processed}/{len(wav_files)} samples successfully ({len(quiet_samples)} quiet samples removed)")
    else:
        print(f"Processed {total_processed}/{len(wav_files)} samples successfully")
    
    return success_count > 0, errors
