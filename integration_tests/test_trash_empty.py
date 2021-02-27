# Copyright (C) 2011 Andrea Francia Trivolzio(PV) Italy
import unittest

from trashcli.empty import EmptyCmd

from unit_tests.myStringIO import StringIO
import os
from .files import make_file, require_empty_dir, make_dirs, set_sticky_bit, MyPath
from .files import make_empty_file
from mock import MagicMock
from trashcli.fs import FileSystemReader
from trashcli.fs import FileRemover
import six

from trashcli.empty import main as empty
from trashcli.fs import mkdirs
import shutil

class TestTrashEmptyCmd(unittest.TestCase):
    def test(self):
        out = StringIO()
        empty(['trash-empty', '-h'], stdout = out)
        six.assertRegex(self, out.getvalue(), '^Usage. trash-empty.*')

    def test_trash_empty_will_crash_on_unreadable_directory_issue_48(self):
        out = StringIO()
        err = StringIO()
        mkdirs('data/Trash/files')
        mkdirs('data/Trash/files/unreadable')
        os.chmod('data/Trash/files/unreadable', 0o300)

        assert os.path.exists('data/Trash/files/unreadable')

        empty(['trash-empty'], stdout = out, stderr = err,
                environ={'XDG_DATA_HOME':'data'})

        assert ("trash-empty: cannot remove data/Trash/files/unreadable\n" ==
                     err.getvalue())
        os.chmod('data/Trash/files/unreadable', 0o700)
        shutil.rmtree('data')

    def test_the_core_of_failures_for_issue_48(self):
        mkdirs('unreadable-dir')
        os.chmod('unreadable-dir', 0o300)

        assert os.path.exists('unreadable-dir')

        try:
            FileRemover().remove_file('unreadable-dir')
            assert False
        except OSError:
            pass

        os.chmod('unreadable-dir', 0o700)
        shutil.rmtree('unreadable-dir')


class TestWhenCalledWithoutArguments(unittest.TestCase):

    def setUp(self):
        require_empty_dir('XDG_DATA_HOME')
        self.info_dir_path   = 'XDG_DATA_HOME/Trash/info'
        self.files_dir_path  = 'XDG_DATA_HOME/Trash/files'
        self.environ = {'XDG_DATA_HOME':'XDG_DATA_HOME'}
        now = MagicMock(side_effect=RuntimeError)
        self.empty_cmd = EmptyCmd(
            out = StringIO(),
            err = StringIO(),
            environ = self.environ,
            list_volumes = no_volumes,
            now = now,
            file_reader = FileSystemReader(),
            getuid = None,
            file_remover = FileRemover(),
            version = None,
        )

    def user_run_trash_empty(self):
        self.empty_cmd.run('trash-empty')

    def test_it_should_remove_an_info_file(self):
        self.having_a_trashinfo_in_trashcan('foo.trashinfo')

        self.user_run_trash_empty()

        self.assert_dir_empty(self.info_dir_path)

    def test_it_should_remove_all_the_infofiles(self):
        self.having_three_trashinfo_in_trashcan()

        self.user_run_trash_empty()

        self.assert_dir_empty(self.info_dir_path)

    def test_it_should_remove_the_backup_files(self):
        self.having_one_trashed_file()

        self.user_run_trash_empty()

        self.assert_dir_empty(self.files_dir_path)

    def test_it_should_keep_unknown_files_found_in_infodir(self):
        self.having_file_in_info_dir('not-a-trashinfo')

        self.user_run_trash_empty()

        self.assert_dir_contains(self.info_dir_path, 'not-a-trashinfo')

    def test_but_it_should_remove_orphan_files_from_the_files_dir(self):
        self.having_orphan_file_in_files_dir()

        self.user_run_trash_empty()

        self.assert_dir_empty(self.files_dir_path)

    def test_it_should_purge_also_directories(self):
        os.makedirs("XDG_DATA_HOME/Trash/files/a-dir")

        self.user_run_trash_empty()

        self.assert_dir_empty(self.files_dir_path)

    def assert_dir_empty(self, path):
        assert len(os.listdir(path)) == 0

    def assert_dir_contains(self, path, filename):
        assert os.path.exists(os.path.join(path, filename))

    def having_a_trashinfo_in_trashcan(self, basename_of_trashinfo):
        make_empty_file(os.path.join(self.info_dir_path, basename_of_trashinfo))

    def having_three_trashinfo_in_trashcan(self):
        self.having_a_trashinfo_in_trashcan('foo.trashinfo')
        self.having_a_trashinfo_in_trashcan('bar.trashinfo')
        self.having_a_trashinfo_in_trashcan('baz.trashinfo')
        six.assertCountEqual(self,
                             ['foo.trashinfo',
                              'bar.trashinfo',
                              'baz.trashinfo'], os.listdir(self.info_dir_path))

    def having_one_trashed_file(self):
        self.having_a_trashinfo_in_trashcan('foo.trashinfo')
        make_empty_file(self.files_dir_path + '/foo')
        self.files_dir_should_not_be_empty()

    def files_dir_should_not_be_empty(self):
        assert len(os.listdir(self.files_dir_path)) != 0

    def having_file_in_info_dir(self, filename):
        make_empty_file(os.path.join(self.info_dir_path, filename))

    def having_orphan_file_in_files_dir(self):
        complete_path = os.path.join(self.files_dir_path,
                                     'a-file-without-any-associated-trashinfo')
        make_empty_file(complete_path)
        assert os.path.exists(complete_path)

class TestWhen_invoked_with_N_days_as_argument(unittest.TestCase):
    def setUp(self):
        require_empty_dir('XDG_DATA_HOME')
        self.xdg_data_home   = 'XDG_DATA_HOME'
        self.environ = {'XDG_DATA_HOME':'XDG_DATA_HOME'}
        self.now = MagicMock(side_effect=RuntimeError)
        self.empty_cmd=EmptyCmd(
            out = StringIO(),
            err = StringIO(),
            environ = self.environ,
            list_volumes = no_volumes,
            now = self.now,
            file_reader = FileSystemReader(),
            getuid = None,
            file_remover = FileRemover(),
            version = None,
        )

    def user_run_trash_empty(self, *args):
        self.empty_cmd.run('trash-empty', *args)

    def set_clock_at(self, yyyy_mm_dd):
        self.now.side_effect = lambda:date(yyyy_mm_dd)

        def date(yyyy_mm_dd):
            from datetime import datetime
            return datetime.strptime(yyyy_mm_dd, '%Y-%m-%d')

    def test_it_should_keep_files_newer_than_N_days(self):
        self.having_a_trashed_file('foo', '2000-01-01')
        self.set_clock_at('2000-01-01')

        self.user_run_trash_empty('2')

        self.file_should_have_been_kept_in_trashcan('foo')

    def test_it_should_remove_files_older_than_N_days(self):
        self.having_a_trashed_file('foo', '1999-01-01')
        self.set_clock_at('2000-01-01')

        self.user_run_trash_empty('2')

        self.file_should_have_been_removed_from_trashcan('foo')

    def test_it_should_kept_files_with_invalid_deletion_date(self):
        self.having_a_trashed_file('foo', 'Invalid Date')
        self.set_clock_at('2000-01-01')

        self.user_run_trash_empty('2')

        self.file_should_have_been_kept_in_trashcan('foo')

    def having_a_trashed_file(self, name, date):
        contents = "DeletionDate=%sT00:00:00\n" % date
        make_file(self.trashinfo(name), contents)

    def trashinfo(self, name):
        return '%(dirname)s/Trash/info/%(name)s.trashinfo' % {
                    'dirname' : self.xdg_data_home,
                    'name'    : name }

    def file_should_have_been_kept_in_trashcan(self, trashinfo_name):
        assert os.path.exists(self.trashinfo(trashinfo_name))
    def file_should_have_been_removed_from_trashcan(self, trashinfo_name):
        assert not os.path.exists(self.trashinfo(trashinfo_name))


class TestEmptyCmdWithMultipleVolumes(unittest.TestCase):
    def setUp(self):
        self.temp_dir = MyPath.make_temp_dir()
        self.top_dir = self.temp_dir / 'topdir'
        require_empty_dir(self.top_dir)
        self.empty=EmptyCmd(
                out          = StringIO(),
                err          = StringIO(),
                environ      = {},
                list_volumes = lambda: [self.top_dir],
                now          = None,
                file_reader  = FileSystemReader(),
                getuid       = lambda: 123,
                file_remover = FileRemover(),
                version      = None,
        )

    def test_it_removes_trashinfos_from_method_1_dir(self):
        self.make_proper_top_trash_dir(self.top_dir / '.Trash')
        make_empty_file(self.top_dir / '.Trash/123/info/foo.trashinfo')

        self.empty.run('trash-empty')

        assert not os.path.exists(
            self.top_dir / '.Trash/123/info/foo.trashinfo')
    def test_it_removes_trashinfos_from_method_2_dir(self):
        make_empty_file(self.top_dir / '.Trash-123/info/foo.trashinfo')

        self.empty.run('trash-empty')

        assert not os.path.exists(
            self.top_dir / '.Trash-123/info/foo.trashinfo')

    def test_it_removes_trashinfo_from_specified_trash_dir(self):
        make_empty_file(self.temp_dir / 'specified/info/foo.trashinfo')

        self.empty.run('trash-empty', '--trash-dir',
                       self.temp_dir / 'specified')

        assert not os.path.exists(
            self.temp_dir / 'specified/info/foo.trashinfo')


    def make_proper_top_trash_dir(self, path):
        make_dirs(path)
        set_sticky_bit(path)

    def tearDown(self):
        self.temp_dir.clean_up()

from textwrap import dedent
class TestTrashEmpty_on_help(unittest.TestCase):
    def test_help_output(self):
        err, out = StringIO(), StringIO()
        cmd = EmptyCmd(err = err,
                       out = out,
                       environ = {},
                       list_volumes = no_volumes,
                       now = None,
                       file_reader = FileSystemReader(),
                       getuid = None,
                       file_remover = None,
                       version = None,
                       )
        cmd.run('trash-empty', '--help')
        assert out.getvalue() == dedent("""\
            Usage: trash-empty [days]

            Purge trashed files.

            Options:
              --version   show program's version number and exit
              -h, --help  show this help message and exit

            Report bugs to https://github.com/andreafrancia/trash-cli/issues
            """)

class TestTrashEmpty_on_version(unittest.TestCase):
    def test_it_print_version(self):
        err, out = StringIO(), StringIO()
        cmd = EmptyCmd(err = err,
                       out = out,
                       environ = {},
                       list_volumes = no_volumes,
                       now = None,
                       file_reader = FileSystemReader(),
                       getuid = None,
                       file_remover = None,
                       version = '1.2.3',
                       )
        cmd.run('trash-empty', '--version')
        assert out.getvalue() == dedent("""\
            trash-empty 1.2.3
            """)


class Test_describe_trash_empty_command_line__on_invalid_options(unittest.TestCase):
    def setUp(self):
        self.err, self.out = StringIO(), StringIO()
        self.cmd = EmptyCmd(
                       err = self.err,
                       out = self.out,
                       environ = {},
                       list_volumes = no_volumes,
                       now = None,
                       file_reader = FileSystemReader(),
                       getuid = None,
                       file_remover = None,
                       version = None,
                       )

    def test_it_should_fail(self):

        self.exit_code = self.cmd.run('trash-empty', '-2')

        exit_code_for_command_line_usage = 64
        assert exit_code_for_command_line_usage == self.exit_code

    def test_it_should_complain_to_the_standard_error(self):

        self.exit_code = self.cmd.run('trash-empty', '-2')

        assert self.err.getvalue() == dedent("""\
                trash-empty: invalid option -- '2'
                """)

    def test_with_a_different_option(self):

        self.cmd.run('trash-empty', '-3')

        assert self.err.getvalue() == dedent("""\
                trash-empty: invalid option -- '3'
                """)

def no_volumes():
    return []

