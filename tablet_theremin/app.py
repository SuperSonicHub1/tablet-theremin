"""
https://developer-docs.wacom.com/docs/icbt/linux/gtk/gtk-overview/
https://developer-docs.wacom.com/docs/icbt/linux/gtk/gtk-reference/
"""

from enum import Enum, auto

import gi
import mido
from mido.ports import BaseOutput
from scamp_extensions.pitch import Scale

from .frequencies import (
    axis_to_midi_note,
    axis_to_midi_velocity,
    midi_note_to_freq,
    Algorithm,
)

gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk, Gdk, Gio  # noqa: E402


class Mode(Enum):
    RAPID_FIRE = auto()
    ONE_VOICE = auto()


# TODO: Allow user to configure this
CHANNEL = 0


class Application(Gtk.Application):
    stylus: Gtk.GestureStylus
    pad: Gtk.PadController
    action_group: Gio.SimpleActionGroup
    window: Gtk.ApplicationWindow
    info: Gtk.Label
    debug_info: Gtk.Label
    output: BaseOutput
    previous_note: int | None
    left_midi_note: int
    right_midi_note: int
    algorithm: Algorithm
    mode: Mode
    scale: Scale | None

    def __init__(self):
        super().__init__(application_id="com.kawcco.TabletTheremin")
        GLib.set_application_name('Tablet Theremin')

        # Defualts
        self.previous_note = None
        self.left_midi_note = 36  # C2
        self.right_midi_note = 84  # C6
        self.algorithm = Algorithm.LOGARITHMIC
        self.mode = Mode.ONE_VOICE
        self.scale = None  # Scale.major(self.left_midi_note)

        # Gestures
        self.stylus = Gtk.GestureStylus()
        self.stylus.set_stylus_only(True)
        self.stylus.connect('motion', self.do_motion)
        self.stylus.connect('up', self.do_up)

        # Figure out why this isn't wokring
        # The actions are designed with my Wacom Intuos (4 buttons) in mind
        # https://docs.gtk.org/gtk4/class.PadController.html
        # BUTTON = Gtk.PadActionType.BUTTON
        # ACTIONS = [
        #     (BUTTON, 0, -1, "Octave Down", 'octave_down'),
        #     (BUTTON, 1, -1, "Octave Up", 'octave_up'),
        #     (BUTTON, 2, -1, "Switch Algorithm", 'switch_algo'),
        # ]
        # self.action_group = Gio.SimpleActionGroup()
        # self.pad = Gtk.PadController()
        # self.pad.action_group = self.action_group
        # for action in ACTIONS:
        #     fn = getattr(self, f'do_{action[-1]}')
        #     simple_action = Gio.SimpleAction(name=action[-1])
        #     simple_action.connect(
        #         "activate",
        #         lambda _simple_action, _parameter: print(action[-1]),LOGARITHMIC
        #         # lambda _simple_action, _parameter: (fn(), self.update_info()),
        #     )
        #     self.action_group.add_action(simple_action)
        #     self.pad.set_action(*action)

    def do_motion(self, stylus, x, y):
        """
        Play notes when pressing down on tablet.
        """
        width, height = self.window.get_width(), self.window.get_height()

        # from -1 to 1 inclusive without max
        percent_x = max(0., x / width)
        percent_y = max(0., y / height)

        # from 0 to 1 inclusive
        pressure_exists, pressure = stylus.get_axis(Gdk.AxisUse.PRESSURE)
        assert pressure_exists

        midi_note = axis_to_midi_note(
            percent_x,
            midi_note_to_freq(self.left_midi_note),
            midi_note_to_freq(self.right_midi_note),
            self.algorithm,
        )
        if self.scale is not None:
            midi_note = int(self.scale.floor(midi_note))
        midi_velocity = axis_to_midi_velocity(pressure)
        modwheel = axis_to_midi_velocity(percent_y)

        # Send notes
        if self.mode not in Mode:
            raise KeyError(f"Mode {self.mode} unsupported.")

        if (
            self.mode == Mode.RAPID_FIRE
            or (
                self.mode == Mode.ONE_VOICE
                and self.previous_note != midi_note
            )
        ):
            if self.previous_note is not None:
                self.output.send(
                    mido.Message(
                        'note_off',
                        note=self.previous_note,
                        channel=CHANNEL
                    )
                )
            self.output.send(
                mido.Message(
                    'note_on',
                    note=midi_note,
                    velocity=midi_velocity,
                    channel=CHANNEL
                )
            )
            self.previous_note = midi_note
        # Update velocity with aftertouch
        elif self.mode == Mode.ONE_VOICE and self.previous_note == midi_note:
            self.output.send(
                mido.Message(
                    'aftertouch',
                    value=midi_velocity,
                    channel=CHANNEL
                )
            )

        self.output.send(
            mido.Message(
                'control_change',
                value=modwheel,
                channel=1,
            )
        )

        # UI
        debug_text = (
            f"""
X: {percent_x * 100:.0f}%
Y: {percent_y * 100:.0f}%
Pressure: {pressure * 100:.0f}%
MIDI Note (X): {midi_note}
MIDI Velocity (Pressure): {midi_velocity}
Modwheel (Y): {modwheel}"""
        )

        self.debug_info.set_label(debug_text)

    def do_up(self, _stylus, _x, _y):
        """
        Silence once you lift your stylus off.
        """
        self.output.send(
            mido.Message('note_off', note=self.previous_note, channel=CHANNEL)
        )
        self.previous_note = None
        self.output.send(
            mido.Message(
                'control_change',
                value=1,
                channel=CHANNEL,
            )
        )

    def update_info(self):
        info_text = (
            f"""MIDI Range: {self.left_midi_note} - {self.right_midi_note}
Algorithm: {self.algorithm}
Mode: {self.mode}
Quantized: {self.scale is not None}"""
        )
        self.info.set_label(info_text)

    def do_octave_down(self):
        if self.left_midi_note != 0:
            self.left_midi_note -= 12
            self.right_midi_note -= 12

    def do_octave_up(self):
        if self.left_midi_note != 120:
            self.left_midi_note += 12
            self.right_midi_note += 12

    def do_switch_algo(self):
        self.algorithm = (
            Algorithm.LINEAR
            if self.algorithm == Algorithm.LOGARITHMIC
            else Algorithm.LINEAR
        )

    def handle_output_selection(
        self,
        config_window: Gtk.Window,
        output_name: str
    ):
        self.output = mido.open_output(output_name)
        config_window.close()
        self.present_main_window()

    def present_main_window(self):

        self.window.present()
        self.window.fullscreen()

    def do_activate(self):
        # Main UI
        self.window = Gtk.ApplicationWindow(
            application=self,
            title="Tablet Theremin"
        )
        # https://github.com/Taiko2k/GTK4PythonTutorial#input-handling-in-our-drawing-area
        self.cursor_crosshair = Gdk.Cursor.new_from_name("crosshair")
        self.window.set_cursor(self.cursor_crosshair)

        app_body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.window.set_child(app_body)
        self.info = Gtk.Label()
        app_body.append(self.info)
        self.update_info()
        self.debug_info = Gtk.Label()
        app_body.append(self.debug_info)

        # Add gestures to window
        self.window.add_controller(self.stylus)

        # Initial config window
        config_window = Gtk.Window()
        config_window.set_modal(True)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        config_window.set_child(body)
        body.append(
            Gtk.Label(
                label="<big>Select Output</big>",
                use_markup=True
            )
        )
        outputs = Gtk.DropDown.new_from_strings(
            mido.get_output_names()
        )
        body.append(outputs)
        config_window.present()

        select_button = Gtk.Button.new_with_label("Select")
        body.append(select_button)
        select_button.connect(
            'clicked',
            lambda _: self.handle_output_selection(
                config_window,
                outputs.get_selected_item().get_string()
            )
        )
