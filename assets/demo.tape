# vhs tape script for the canonical `voa research demo` recording.
#
# Regenerate the demo GIF with:
#   vhs assets/demo.tape
#
# Cost: ~$0.30 per run (Opus default; 10 subjects). Duration: ~60-90s
# real time, ~30-45s in the GIF after PlaybackSpeed 2.0.

Output assets/demo.gif

Set FontSize 13
Set Width 1000
Set Height 720
Set Theme "Dracula"
Set TypingSpeed 60ms
Set PlaybackSpeed 2.0
Set Padding 18
Set Shell "zsh"

# Clean prompt for the recording
Hide
Type "clear"
Enter
Show

Sleep 500ms

# Type the canonical command at natural human speed
Type "voa research demo"
Sleep 800ms
Enter

# Wait for the live demo to complete (Rich progress spinner + 4-stage
# pipeline + final synthesized output). 180s covers an Opus run with
# 12 subjects + headroom; PlaybackSpeed 2.0 compresses this to ~90s
# in the GIF.
Sleep 180s
