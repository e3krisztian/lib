from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals
from __future__ import print_function

import contextlib
import os
import fixtures

from . import tech

from .test import TempDir, CaptureStdout, CaptureStderr
from . import cli


@contextlib.contextmanager
def chdir(directory):
    cwd = os.getcwd()
    try:
        os.chdir(directory)
        yield
    finally:
        os.chdir(cwd)


@contextlib.contextmanager
def environment(robot):
    '''
    Context manager - enable running code in the context of the robot.
    '''
    with fixtures.EnvironmentVariable('HOME', robot.home):
        with chdir(robot.cwd):
            try:
                cli.initialize_env(robot.config_dir)
                yield
            except BaseException as e:
                robot.retval = e
                raise


class Robot(fixtures.Fixture):
    '''
    Represents a fake user.

    All operations are isolated from the test runner user's environment.
    They work in a dedicated environment with temporary home, config
    and working directories.
    '''

    def setUp(self):
        super(Robot, self).setUp()
        self.base_dir = self.useFixture(TempDir()).path
        os.makedirs(self.home)
        self.cd(self.home)

    def cleanUp(self):
        super(Robot, self).cleanUp()
        self.base_dir = None

    @property
    def config_dir(self):
        return self.base_dir / 'config'

    @property
    def home(self):
        return self.base_dir / 'home'

    def _path(self, path):
        '''
        Convert relative paths to absolute paths
        '''
        if os.path.isabs(path):
            return path
        else:
            return tech.fs.Path(os.path.normpath(self.cwd / path))

    def cd(self, dir):
        '''
        Change to directory
        '''
        self.cwd = self._path(dir)
        assert os.path.isdir(self.cwd)

    @property
    def environment(self):
        '''
        Context manager - enable running code in the context of this robot.
        '''
        return environment(self)

    def cli(self, *args):
        '''
        Imitate calling the command line tool with the given args
        '''
        with self.environment:
            with CaptureStdout() as stdout, CaptureStderr() as stderr:
                try:
                    self.retval = cli.run(args)
                finally:
                    self.stdout = stdout.text
                    self.stderr = stderr.text

    def ls(self, directory=None):
        directory = self._path(directory or self.cwd)
        return [
            directory / filename
            for filename in os.listdir(directory)]

    def write_file(self, path, content):
        assert not os.path.isabs(path)
        tech.fs.write_file(self.cwd / path, content)
