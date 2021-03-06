from bead.exceptions import InvalidArchive
import os
import sys

from bead import tech
from bead.workspace import Workspace
from bead import layouts
import bead.spec as bead_spec

from .cmdparse import Command
from .common import assert_valid_workspace, die, warning
from .common import DefaultArgSentinel
from .common import OPTIONAL_WORKSPACE, OPTIONAL_ENV
from .common import BEAD_REF_BASE, BEAD_TIME, resolve_bead
from .common import verify_with_feedback
from . import arg_metavar
from . import arg_help

timestamp = tech.timestamp.timestamp


def assert_may_be_valid_name(name):
    '''
    Refuse bead names that are non cross platform file-system compatible
    '''
    valid_syntax = (
        name
        and os.path.sep not in name
        and '/' not in name
        and '\\' not in name
        and ':' not in name
    )
    if not valid_syntax:
        die(f'Invalid name "{name}"')


class CmdNew(Command):
    '''
    Create and initialize new workspace directory for a new bead.
    '''

    def declare(self, arg):
        arg('workspace', type=Workspace, metavar=arg_metavar.WORKSPACE,
            help='bead and directory to create')

    def run(self, args):
        workspace: Workspace = args.workspace
        assert_may_be_valid_name(workspace.name)
        if os.path.exists(workspace.directory):
            die(f'Directory {workspace.name} already exists.')

        kind = tech.identifier.uuid()
        workspace.create(kind)
        print(f'Created "{workspace.name}"')


def WORKSPACE_defaulting_to(default_workspace):
    def opt_workspace(parser):
        parser.arg(
            'workspace', nargs='?', type=Workspace,
            default=default_workspace,
            metavar=arg_metavar.WORKSPACE, help=arg_help.WORKSPACE)
    return opt_workspace


USE_THE_ONLY_BOX = DefaultArgSentinel(
    'if there is exactly one box,' +
    ' store there, otherwise it MUST be specified')


class CmdSave(Command):
    '''
    Save workspace in a box.
    '''

    def declare(self, arg):
        arg('box_name', nargs='?', default=USE_THE_ONLY_BOX, type=str,
            metavar=arg_metavar.BOX, help=arg_help.BOX)
        arg(OPTIONAL_WORKSPACE)
        arg(OPTIONAL_ENV)

    def run(self, args):
        box_name = args.box_name
        workspace = args.workspace
        env = args.get_env()
        assert_valid_workspace(workspace)
        # XXX: (usability) save - support saving directly to a directory outside of workspace
        if box_name is USE_THE_ONLY_BOX:
            boxes = env.get_boxes()
            if not boxes:
                warning('No boxes have been defined')
                beadbox = os.path.expanduser('~/BeadBox')
                sys.stderr.write(
                    f'Creating and using a new one with name `home` and location {beadbox}')
                tech.fs.ensure_directory(beadbox)
                env.add_box('home', beadbox)
                env.save()
                # continue with newly created box
                boxes = env.get_boxes()
                assert len(boxes) == 1
            if len(boxes) > 1:
                die(
                    'BOX parameter is not optional!\n' +
                    '(more than one boxes exists)')
            box = boxes[0]
        else:
            box = env.get_box(box_name)
            if box is None:
                die(f'Unknown box: {box_name}')
        location = box.store(workspace, timestamp())
        print(f'Successfully stored bead at {location}.')


DERIVE_FROM_BEAD_NAME = DefaultArgSentinel('derive one from bead name')


class CmdDevelop(Command):
    '''
    Unpack a bead as a source tree.

    Bead directory layout is created, but only the source files are
    extracted.
    '''

    def declare(self, arg):
        arg(BEAD_REF_BASE)
        arg(BEAD_TIME)
        arg(WORKSPACE_defaulting_to(DERIVE_FROM_BEAD_NAME))
        arg('-x', '--extract-output', dest='extract_output',
            default=False, action='store_true',
            help='Extract output data as well (normally it is not needed!).')
        arg(OPTIONAL_ENV)

    def run(self, args):
        extract_output = args.extract_output
        env = args.get_env()
        try:
            bead = resolve_bead(env, args.bead_ref_base, args.bead_time)
        except LookupError:
            die('Bead not found!')
        try:
            verify_with_feedback(bead)
        except InvalidArchive:
            die('Bead is damaged')
        if args.workspace is DERIVE_FROM_BEAD_NAME:
            workspace = Workspace(bead.name)
        else:
            workspace = args.workspace

        if os.path.exists(workspace.directory):
            die(f'Workspace "{workspace.name}" directory already exists'
                ' - do you have an old checkout?')
        bead.unpack_to(workspace)
        assert workspace.is_valid

        if extract_output:
            output_directory = workspace.directory / layouts.Workspace.OUTPUT
            bead.unpack_data_to(output_directory)

        print(f'Extracted source into {workspace.directory}')
        # XXX: try to load smaller inputs?
        if workspace.inputs:
            print('Input data not loaded, update if needed and load manually')


def print_inputs(env, workspace, verbose):
    assert_valid_workspace(workspace)
    inputs = sorted(workspace.inputs)

    if inputs:
        boxes = env.get_boxes()

        print('Inputs:')
        has_not_loaded = False
        is_not_first_input = True
        for input in inputs:
            if is_not_first_input:
                print('')
            is_not_loaded = not workspace.is_loaded(input.name)
            has_not_loaded = has_not_loaded or is_not_loaded
            print(f'input/{input.name}')
            print(f'\tStatus:      {"**NOT LOADED**" if is_not_loaded else "loaded"}')
            input_bead_name = workspace.get_input_bead_name(input.name)
            print(f'\tBead:        {input_bead_name} # {input.freeze_time_str}')
            if verbose:
                print(f'\tKind:        {input.kind}')
                print(f'\tContent id:  {input.content_id}')
            print('\tBox[es]:')
            has_box = False
            for box in boxes:
                try:
                    context = box.get_context(
                        bead_spec.BEAD_NAME, input_bead_name, input.freeze_time)
                except LookupError:
                    # not in this box
                    continue
                bead = context.best
                has_box = True
                exact_match = bead.content_id == input.content_id
                print(f'\t {"*" if exact_match else "?"} -r {box.name} # {bead.freeze_time_str}')
            if not has_box:
                print('\t - no candidates :(')
                print('\t   Maybe it has been renamed? or is it in an unreachable box?')
            is_not_first_input = True

        print('')
        if has_not_loaded:
            print('Some inputs are currently not loaded.')
            print('You can "load" or "update" them manually.')
    else:
        print('No inputs defined')


class CmdStatus(Command):
    '''
    Show workspace status - name of bead, inputs and their unpack status.
    '''

    def declare(self, arg):
        arg(OPTIONAL_WORKSPACE)
        arg('-v', '--verbose', default=False, action='store_true',
            help='show more detailed information')
        arg(OPTIONAL_ENV)

    def run(self, args):
        workspace = args.workspace
        verbose = args.verbose
        env = args.get_env()
        kind_needed = verbose
        if workspace.is_valid:
            print(f'Bead Name: {workspace.name}')
            if kind_needed:
                print(f'Bead kind: {workspace.kind}')
            print()
            print_inputs(env, workspace, verbose)
        else:
            warning(f'Invalid workspace ({workspace.directory})')


class CmdZap(Command):
    '''
    Delete the workspace, inluding data, code and documentation.
    '''

    def declare(self, arg):
        arg(WORKSPACE_defaulting_to(Workspace.for_current_working_directory()))

    def run(self, args):
        workspace = args.workspace
        assert_valid_workspace(workspace)
        directory = workspace.directory
        # on non-posix systems (Windows) it might happen, that we can not remove
        # the directory we are in -> ignore errors
        tech.fs.rmtree(directory, ignore_errors=os.name != 'posix')
        print(f'Deleted workspace {directory}')


class CmdNuke(Command):
    '''
    No operation, you probably want zap, to delete the workspace.

    Nuke was a bad name.
    '''

    def run(self, args):
        print('Nothing happened.')
        print()
        print('You probably want to use zap, the nuke command is about to disappear.')
