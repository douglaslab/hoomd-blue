from abc import ABC, abstractmethod
from itertools import repeat, cycle
from inspect import isclass
from hoomd.util import is_iterable, is_mapping
from hoomd.typeconverter import RequiredArg


class SmartDefault(ABC):
    @abstractmethod
    def __init__(self, *args, **kwargs):
        pass

    @abstractmethod
    def __call__(self, value):
        pass

    @abstractmethod
    def to_base(self):
        pass


class SmartDefaultSequence(SmartDefault):
    def __init__(self, sequence, default):
        if is_iterable(default):
            dft_iter = cycle(default)
        else:
            dft_iter = repeat(default)
        self.default = [toDefault(item, dft)
                        for item, dft in zip(sequence, dft_iter)]

    def __call__(self, sequence):
        if sequence is None:
            return self.to_base()
        else:
            new_sequence = []
            if len(self.default) == 1:
                for v, d in zip(sequence, self):
                    if isinstance(d, SmartDefault):
                        new_sequence.append(d(v))
                    else:
                        new_sequence.append(v)
            else:
                given_length = len(sequence)
                for i, d in enumerate(self):
                    if i < given_length:
                        if isinstance(d, SmartDefault):
                            new_sequence.append(d(sequence[i]))
                        else:
                            new_sequence.append(sequence[i])
                    else:
                        if isinstance(d, SmartDefault):
                            new_sequence.append(d.to_base())
                        else:
                            new_sequence.append(d)
            return new_sequence

    def __iter__(self):
        if len(self.default) == 1:
            yield from repeat(self.default[0])
        else:
            yield from self.default

    def to_base(self):
        return [fromDefault(item) for item in self.default]


class SmartDefaultFixedLengthSequence(SmartDefault):
    def __init__(self, sequence, default):
        if is_iterable(default):
            dft_iter = cycle(default)
        else:
            dft_iter = repeat(default)
        self.default = tuple([toDefault(item, dft)
                              for item, dft in zip(sequence, dft_iter)])

    def __call__(self, sequence):
        if sequence is None:
            return self.to_base()
        else:
            new_sequence = []
            given_length = len(sequence)
            for i, d in enumerate(self):
                if i < given_length:
                    if isinstance(d, SmartDefault):
                        new_sequence.append(d(sequence[i]))
                    else:
                        new_sequence.append(sequence[i])
                else:
                    if isinstance(d, SmartDefault):
                        new_sequence.append(d.to_base())
                    else:
                        new_sequence.append(d)
            return new_sequence

    def __iter__(self):
        yield from self.default

    def to_base(self):
        return tuple([fromDefault(v) for v in self])


class SmartDefaultMapping(SmartDefault):
    def __init__(self, mapping, defaults):
        if is_mapping(defaults):
            self.default = {key: toDefault(value, defaults.get(key))
                            for key, value in mapping.items()}
        else:
            self.default = {key: toDefault(value, defaults)
                            for key, value in mapping.items()}

    def __call__(self, mapping):
        if mapping is None:
            return self.to_base()
        else:
            new_mapping = dict()
            for key, sdft in self.default.items():
                if key in mapping:
                    if isinstance(sdft, SmartDefault):
                        new_mapping[key] = sdft(mapping[key])
                    else:
                        new_mapping[key] = mapping[key]
                else:
                    if isinstance(sdft, SmartDefault):
                        new_mapping[key] = sdft(None)
                    else:
                        new_mapping[key] = sdft
            return new_mapping

    def keys(self):
        yield from self.default.keys()

    def __getitem__(self, key):
        return self.default[key]

    def __setitem__(self, key, value):
        self.default[key] = value

    def __contains__(self, value):
        return value in self.default

    def to_base(self):
        return {key: fromDefault(value) for key, value in self.default.items()}


def toDefault(value, explicit_defaults=None):
    if isinstance(value, tuple):
        return SmartDefaultFixedLengthSequence(value, explicit_defaults)
    if is_iterable(value):
        return SmartDefaultSequence(value, explicit_defaults)
    elif is_mapping(value):
        return SmartDefaultMapping(value, explicit_defaults)
    elif isclass(value) or callable(value):
        return RequiredArg if explicit_defaults is None else explicit_defaults
    else:
        return value if explicit_defaults is None else explicit_defaults


def fromDefault(value):
    if isinstance(value, SmartDefault):
        return value.to_base()
    else:
        return value
