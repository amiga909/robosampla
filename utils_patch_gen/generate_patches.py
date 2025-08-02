#!/usr/bin/env python3
"""
Simple patch generator - Edit the arrays and template below, then run.
"""
import json

# 🎵 PATCH NAMES - Edit this array with your patch names
PATCH_NAMES = [
    "Piano 2",
    "Piano 3",
    "Honky-Tonk Piano",
    "Elec. Piano",
    "Harpsichord 1",
    "Harpsichord 2",
    "Synth. Clavi.",
    "Metal Honky-Tonk",
    "Double Attack",
    "Bells",
    "Carillon",
    "Synth. Celesta",
    "Synth. Vib.1",
    "Synth. Vib.2",
    "Synth. Vib.3 ★",
    "Bell-Lyra",
    "Xylophone",
    "Soft Xylophone",
    "Marimba",
    "Aco. Guitar 1",
    "Aco. Guitar 2",
    "Semiaco Guitar",
    "Feedback",
    "Elec. Guitar 1",
    "Elec. Guitar 2",
    "Elec. Bass 1",
    "Elec. Bass 2",
    "Slap Bass",
    "Metallic Bass",
    "Synth. Drums 1",
    "Synth. Drums 2",
    "Synth. Drums 3",
    "Synth. Clapper",
    "Tambourine",
    "Cowbell",
    "Conga",
    "Tabla",
    "Afro-Percussion",
    "Steel Drum",
    "Motorcycle",
    "Jet Roar",
    "Explosion",
    "Typhoon Sound",
    "Cavernous Sound",
    "Scratch Sound",
    "Computer Sound",
    "Laser Gun",
    "Miracle",
    "Sweep"
]

# 🔧 SETTINGS
PROGRAM_CHANGE_OFFSET = 51  # Starting program change number
OUTPUT_FILE = "_generated_patches.json"

# 📋 DEFAULT ENTRY TEMPLATE - Edit this to match your desired patch format
DEFAULT_ENTRY = {
    "skip": False,
    "program_change": 50,
    "from_note": 36,
    "to_note": 97,
    "note_gap": 3,
    "note_duration": 20,
    "mono": True,
    "midi_channel": 0,
    "bank_msb": 0,
    "bank_lsb": 0,
    "velocity": 127
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
