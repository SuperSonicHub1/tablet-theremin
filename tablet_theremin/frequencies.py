"""
https://en.wikipedia.org/wiki/Piano_key_frequencies

axis notation: an argument `axis: float` in this file always ranges from 0 to 1
"""

from enum import Enum, auto
from math import log2, floor


class Algorithm(Enum):
    LOGARITHMIC = auto()
    LINEAR = auto()


def lerp(left, right, amount):
    return amount * (right - left) + left


def freq_to_nth_key(f: float) -> float:
    return 12 * log2(f / 440) + 49


def nth_key_to_freq(n: int) -> float:
    return 2 ** ((n - 49) / 12) * 440


def nth_key_to_midi_note(n: float) -> int:
    return floor(n + 20)


def midi_note_to_nth_key(m: int) -> int:
    return m - 20


def midi_note_to_freq(m: int) -> float:
    return nth_key_to_freq(midi_note_to_nth_key(m))


def axis_to_midi_note(
    axis: float,
    left_freq: float,  # C2
    right_freq: float,  # C6
    algorithm: Algorithm,
) -> int:
    if algorithm == Algorithm.LOGARITHMIC:
        return nth_key_to_midi_note(
            freq_to_nth_key(
                lerp(
                    left_freq,
                    right_freq,
                    axis,
                )
            )
        )
    elif algorithm == Algorithm.LINEAR:
        return int(
            lerp(
                nth_key_to_midi_note(freq_to_nth_key(left_freq)),
                nth_key_to_midi_note(freq_to_nth_key(right_freq)),
                axis
            )
        )
    else:
        raise KeyError(f"Algorithm {algorithm} unsupported")


def axis_to_midi_velocity(axis: float) -> int:
    return max(0, min(int(lerp(0, 127, axis)), 127))
