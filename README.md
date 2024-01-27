# Tablet Theremin

Use a GTK-compatible drawing tablet as a MIDI controller.

Theremin is monophonic. X axis is pitch, with either linear or logarithmic scales with support for quantization. Pressure is velocity/aftertouch. Y axis is a modwheel.

Two modes for sending MIDI notes:
- "rapid fire" sends a new MIDI note anytime any of the axes change
- "one note" varies the velocity of the current note with aftertouch until a new note is pressed

Very basic GUI in place ATM; application is currently configured through editing the code.

Linux-only due to dependence on GTK4. 
