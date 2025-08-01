#!/usr/bin/env python3
"""
Simple patch generator - Edit the arrays and template below, then run.
"""
import json

# 🎵 PATCH NAMES - Edit this array with your patch names
PATCH_NAMES = [
    "Subsonic",
    "Megabba1",
    "Megabba2",
    "Megabba3",
    "Modulate",
    "LoClicks",
    "Clicks",
    "HiClicks",
    "Vibraton",
    "OnTheRun",
    "Stumble",
    "& Fall",
    "Pusher",
    "Voltage!",
    "Voltage2",
    "Shortcut",
    "Whatever",
    "Madnezz",
    "Bassline",
    "Basline2",
    "Marsians",
    "HolyBass",
    "Basiac",
    "Signal",
    "Sign",
    "UseThis1",
    "UseThis2",
    "UseThis3",
    "UseThat1",
    "UseThat2",
    "UseThat3",
    "UseThat4",
    "Or That",
    "2001",
    "2010",
    "HAL9000",
    "Its 99!",
    "AiRCrash",
    "Simmons?",
    "Phonecal", 
    "Ultradry",
    "Nameless",
    "Bleeps 1",
    "Bleeps 2",
    "Bleeps 3",
    "Clonks 1",
    "Clonks 2",
    "Clonks 3",
    "Clonks 4",
    "Clonks 5",
    "Claptrap",
    "Einlauf",
    "Toxic 1",
    "Toxic 2",
    "BeamMeUp",
    "Scotty!",
    "Slapback",
    "Berserc",
    "Starter",
    "HH-Drive",
    "Smog",
    "AiRWalk",
    "BreathIn",
    "Lines",
    "PingPong",
    "Flutter",
    "NewToy",
    "Overflow",
    "Fast4Wrd",
    "Knall",
    "& Fall",
    "Shorty",
    "HiOnBase",
    "Kiss Me!",
    "Whip Me!",
    "LowOnIce",
    "Valium 1",
    "Valium 2",
    "TripPlop",
    "Insomnia",
    "Downturn",
    "HrdStepa",
    "HiNRG 1",
    "HiNRG 2",
    "HiNRG 3",
    "5 vor 12",
    "bye...",
    "und weg!",
]

# 🔧 SETTINGS
PROGRAM_CHANGE_OFFSET = 40  # Starting program change number
OUTPUT_FILE = "_generated_patches.json"

# 📋 DEFAULT ENTRY TEMPLATE - Edit this to match your desired patch format
DEFAULT_ENTRY = {
    "midi_channel": 9,
    "type": "airbase",
    "note_gap": 1,
    "note_duration": 3,
    "bank_msb": 0,
    "bank_lsb": 1,  # For Airbase Bank 0, kits 128-255
    "velocity": 127,
    "mono": False,
    "skip": False
}


def generate_patches():
    """Generate patches with auto-incrementing program changes."""
    patches = []
    
    print(f"🎵 Generating {len(PATCH_NAMES)} patches...")
    print(f"📊 Program changes: {PROGRAM_CHANGE_OFFSET} to {PROGRAM_CHANGE_OFFSET + len(PATCH_NAMES) - 1}")
    
    for i, patch_name in enumerate(PATCH_NAMES):
        # Copy the default entry template
        patch = DEFAULT_ENTRY.copy()
        
        # Set the dynamic values
        patch["name"] = patch_name
        patch["program_change"] = PROGRAM_CHANGE_OFFSET + i
        
        patches.append(patch)
        print(f"  ✓ {patch_name} -> Program {PROGRAM_CHANGE_OFFSET + i}")
    
    return patches


def main():
    """Generate and save patches."""
    print("=" * 50)
    print("🎹 SIMPLE PATCH GENERATOR")
    print("=" * 50)
    
    # Generate patches
    patches = generate_patches()
    
    # Save to file
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(patches, f, indent=2)
    
    print(f"\n✅ SUCCESS!")
    print(f"📁 Saved {len(patches)} patches to: {OUTPUT_FILE}")


if __name__ == '__main__':
    main()
