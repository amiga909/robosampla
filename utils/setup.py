#!/usr/bin/env python3
"""
Setup Script - Configure audio devices and MIDI ports
"""
import json
import os
import sys
import sounddevice as sd
import mido

# Add parent directory to path to import from config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CONFIG_FILE = 'local_config.json'
DEFAULT_CONFIG = {
    'audio_device': None,
    'midi_port_name': None,
    'sample_rate': 44100
}


def list_audio_devices():
    """List all available audio devices."""
    print("\n=== Available Audio Devices ===")
    devices = sd.query_devices()
    
    input_devices = []
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            input_devices.append((i, device))
            print(f"{i:2d}: {device['name']} (inputs: {device['max_input_channels']}, rate: {device['default_samplerate']:.0f})")
    
    return input_devices


def list_midi_ports():
    """List all available MIDI output ports."""
    print("\n=== Available MIDI Output Ports ===")
    ports = mido.get_output_names()
    
    for i, port in enumerate(ports):
        print(f"{i:2d}: {port}")
    
    return ports


def test_audio_device(device_id, sample_rate=44100):
    """Test if an audio device works for recording."""
    try:
        print(f"Testing audio device {device_id}...")
        # Try a very short recording
        recording = sd.rec(int(0.1 * sample_rate), samplerate=sample_rate, 
                          channels=1, dtype='float64', device=device_id)
        sd.wait()
        print("✓ Audio device test successful")
        return True
    except Exception as e:
        print(f"✗ Audio device test failed: {e}")
        return False


def test_midi_port(port_name):
    """Test if a MIDI port can be opened."""
    try:
        print(f"Testing MIDI port '{port_name}'...")
        with mido.open_output(port_name) as outport:
            print("✓ MIDI port test successful")
            return True
    except Exception as e:
        print(f"✗ MIDI port test failed: {e}")
        return False


def save_config(config):
    """Save configuration to local config file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"✓ Configuration saved to {CONFIG_FILE}")
        return True
    except Exception as e:
        print(f"✗ Failed to save configuration: {e}")
        return False


def load_config():
    """Load configuration from local config file."""
    try:
        if not os.path.exists(CONFIG_FILE):
            return None
        
        with open(CONFIG_FILE, 'r') as f:
            config = json.load(f)
        return config
    except Exception as e:
        print(f"Warning: Failed to load configuration: {e}")
        return None


def setup_audio_device():
    """Interactive setup for audio device."""
    print("\n" + "="*50)
    print("AUDIO DEVICE SETUP")
    print("="*50)
    
    input_devices = list_audio_devices()
    
    if not input_devices:
        print("No audio input devices found!")
        return None
    
    while True:
        try:
            choice = input(f"\nSelect audio device (0-{len(input_devices)-1}, or 'default' for system default): ").strip().lower()
            
            if choice == 'default':
                if test_audio_device(None):
                    return None  # None means use system default
                else:
                    print("Default audio device test failed. Please select a specific device.")
                    continue
            
            device_idx = int(choice)
            if 0 <= device_idx < len(input_devices):
                device_id, device_info = input_devices[device_idx]
                if test_audio_device(device_id):
                    return device_id
                else:
                    print("Device test failed. Please try another device.")
            else:
                print(f"Invalid choice. Please enter 0-{len(input_devices)-1} or 'default'")
                
        except ValueError:
            print("Invalid input. Please enter a number or 'default'")
        except KeyboardInterrupt:
            print("\nSetup cancelled.")
            return None


def setup_midi_port():
    """Interactive setup for MIDI port."""
    print("\n" + "="*50)
    print("MIDI PORT SETUP")
    print("="*50)
    
    ports = list_midi_ports()
    
    if not ports:
        print("No MIDI output ports found!")
        return None
    
    while True:
        try:
            choice = input(f"\nSelect MIDI port (0-{len(ports)-1}): ").strip()
            port_idx = int(choice)
            
            if 0 <= port_idx < len(ports):
                port_name = ports[port_idx]
                if test_midi_port(port_name):
                    return port_name
                else:
                    print("MIDI port test failed. Please try another port.")
            else:
                print(f"Invalid choice. Please enter 0-{len(ports)-1}")
                
        except ValueError:
            print("Invalid input. Please enter a number")
        except KeyboardInterrupt:
            print("\nSetup cancelled.")
            return None


def run_setup():
    """Run the complete setup process."""
    print("="*60)
    print("         ROBOSAMPLA SETUP")
    print("="*60)
    print("This will configure your audio device and MIDI port settings.")
    print("The configuration will be saved locally and not committed to git.")
    
    config = DEFAULT_CONFIG.copy()
    
    # Setup audio device
    audio_device = setup_audio_device()
    if audio_device is None and input("\nContinue with default audio device? (y/n): ").lower() != 'y':
        print("Setup cancelled.")
        return False
    config['audio_device'] = audio_device
    
    # Setup MIDI port
    midi_port = setup_midi_port()
    if midi_port is None:
        print("Setup cancelled.")
        return False
    config['midi_port_name'] = midi_port
    
    # Save configuration
    if save_config(config):
        print("\n" + "="*60)
        print("         SETUP COMPLETE!")
        print("="*60)
        print(f"Audio Device: {'Default' if config['audio_device'] is None else config['audio_device']}")
        print(f"MIDI Port: {config['midi_port_name']}")
        print(f"Sample Rate: {config['sample_rate']}")
        print("\nYou can run this setup again anytime to change settings.")
        return True
    else:
        return False


def test_setup():
    """Test the current configuration."""
    config = load_config()
    if not config:
        print("No configuration found. Please run setup.")
        return False
    
    print("Testing current configuration...")
    
    # Test audio device
    if not test_audio_device(config.get('audio_device'), config.get('sample_rate', 44100)):
        return False
    
    # Test MIDI port
    if not test_midi_port(config.get('midi_port_name')):
        return False
    
    print("✓ Configuration test successful")
    return True


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup audio and MIDI configuration for RoboSampla")
    parser.add_argument('--test', action='store_true', help='Test current configuration')
    parser.add_argument('--force', action='store_true', help='Force setup even if config exists')
    
    args = parser.parse_args()
    
    if args.test:
        success = test_setup()
        sys.exit(0 if success else 1)
    
    # Check if config exists and is valid
    if not args.force and os.path.exists(CONFIG_FILE):
        if test_setup():
            print("Configuration is valid. Use --force to reconfigure.")
            return
        else:
            print("Configuration test failed. Starting setup...")
    
    # Run setup
    success = run_setup()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
