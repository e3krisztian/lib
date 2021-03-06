from abc import ABCMeta, abstractmethod
from typing import Sequence

from .tech.timestamp import time_from_timestamp
from .meta import BeadName, InputSpec


class Bead:
    '''
    Interface to metadata of a bead.

    Unique identifier:
    box_name, name, content_id

    content_id guarantees same data content, but beads with same content can have
    different metadata, including where it is to be found (box_name) and under which name,
    or how to find the referenced input beads (see input_map).
    '''

    # high level view of computation
    kind: str
    # kind is deprecated. Humans naturally agree on domain specific names instead.
    # The price is living with bad, undescriptive names, that are hard to improve upon later.
    name: BeadName
    inputs: Sequence[InputSpec]

    # frozen beads only details
    # (workspaces fake them with recognisable values)
    content_id: str
    freeze_time_str: str
    box_name: str

    @property
    def freeze_time(self):
        return time_from_timestamp(self.freeze_time_str)

    def get_input(self, name):
        for input in self.inputs:
            if name == input.name:
                return input


class UnpackableBead(Bead, metaclass=ABCMeta):
    '''
    Provide high-level access to content of a bead.
    '''

    def unpack_to(self, workspace):
        self.unpack_code_to(workspace.directory)
        workspace.create_directories()
        self.unpack_meta_to(workspace)

    @abstractmethod
    def unpack_data_to(self, path):
        pass

    @abstractmethod
    def unpack_code_to(self, path):
        pass

    @abstractmethod
    def unpack_meta_to(self, workspace):
        pass
