from __future__ import absolute_import
from __future__ import print_function
import fcntl
import os.path
from hashlib import sha1
from threading import Lock
import time
import tarfile
import shutil
import logging
import weakref
import six.moves.urllib.error
import six.moves.urllib.parse
import six.moves.urllib.request
import email
import errno

from sio.workers import ft, _original_cwd
from sio.workers.elf_loader_patch import _patch_elf_loader
from sio.workers.util import rmtree

SANDBOXES_BASEDIR = os.environ.get(
    'SIOWORKERS_SANDBOXES_BASEDIR', os.path.expanduser(os.path.join('~', '.sio-sandboxes'))
)
SANDBOXES_URL = os.environ.get(
    'SIOWORKERS_SANDBOXES_URL', 'https://downloads.sio2project.mimuw.edu.pl/sandboxes'
)
CHECK_INTERVAL = int(os.environ.get('SIOWORKERS_SANDBOXES_CHECK_INTERVAL', 3600))

logger = logging.getLogger(__name__)


class SandboxError(Exception):
    pass


def _filetracker_path(name):
    return '/sandboxes/%s.tar.gz' % name


def _urllib_path(name):
    return '%s.tar.gz' % name


def _mkdir(name):
    try:
        os.makedirs(name, 0o700)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise


def _sha1_file(filename, block_size=65536):
    import hashlib

    sha1 = hashlib.sha1()
    f = open(filename, 'rb')
    while True:
        chunk = f.read(block_size)
        if not chunk:
            break
        sha1.update(chunk)
    return sha1.hexdigest()


class _FileLock(object):
    """File-based lock (exclusive or shared).

    We use this class for synchronizing processes which use the same
    sandbox. In each installed sandbox directory we create empty file
    named '.lock', and we use `fcntl` locking mechanism on it.
    """

    def __init__(self, filename):
        self.fd = os.open(filename, os.O_WRONLY | os.O_CREAT, 0o600)

    def lock_shared(self):
        fcntl.flock(self.fd, fcntl.LOCK_SH)

    def lock_exclusive(self):
        fcntl.flock(self.fd, fcntl.LOCK_EX)

    def unlock(self):
        fcntl.flock(self.fd, fcntl.LOCK_UN)

    def __del__(self):
        self.unlock()
        os.close(self.fd)


class Sandbox(object):
    """Represents a sandbox... that is some place in the filesystem when
    the previously prepared package with some software is extracted
    (for example compiler, libraries, default output comparator).

    Sandbox in our terminology does not mean isolation or security. It is
    just one directory containing files.

    This class deals only with *using* sandboxes, not creating, changing
    or uploading them. Each sandbox is uniquely identified by ``name``.
    The moment you create the instance of ``Sandbox``, an appropriate
    archive is downloaded and extracted (if not exists; also a check for
    newer version is performed). The path to the extracted sandbox is in
    the ``path`` attribute. This path is valid as long as the ``Sandbox``
    instance exists (is not garbage collected).

    Sandbox images are looked up from two places:

    * from Filetracker, at path ``/sandboxes/<name>``,

    * if not found there, the URL from ``SIO_SANDBOXES_URL`` environment
      variable is used,

    * if such environment variable is not defined, some default URL is used.

    Sandboxes are extracted to the folder named in ``SIO_SANDBOXES_BASEDIR``
    environment variable (or in ``~/.sio-sandboxes`` if the variable is not
    in the environment).

    .. note::

        Processes must not modify the content of the extracted sandbox in
        any way. It is also safe to use the same sandbox by multiple
        processes concurrently, as the folder is locked to ensure no
        problems if an upgrade is needed.

    .. note::

        :class:`Sandbox` is a context manager, so it should be used in a
        ``with`` statement. Upon entering, the sandbox is downloaded,
        extracted and locked, to prevent other processes from performing an
        upgrade.

    .. note::

        Do not constuct instances of this class yourself, use
        :func:`get_sandbox`. Otherwise you may encounter deadlocks when
        having two ``Sandbox`` instances of the same name.
    """

    _instances = weakref.WeakValueDictionary()

    required_fixups = set(('elf_loader_patch',))

    @classmethod
    def _instance(cls, name):
        """This function is used by get_sandbox to get Sandbox instance."""
        i = cls._instances.get(name)
        if i is None:
            i = cls._instances[name] = cls(name)
        return i

    def __init__(self, name):
        self.name = name

        self.path = os.path.join(SANDBOXES_BASEDIR, name)
        _mkdir(SANDBOXES_BASEDIR)
        # This is needed for safe operation with multiple threads,
        # as file locking is useless for this.
        self.local_lock = Lock()
        self._in_context = 0

    def __enter__(self):
        with self.local_lock:
            self._in_context += 1
            if self._in_context == 1:
                try:
                    self.file_lock = _FileLock(self.path + '.lock')
                    self._get()
                except:
                    self._in_context -= 1
                    raise
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        with self.local_lock:
            self._in_context -= 1
            if self._in_context == 0:
                self.file_lock.unlock()

    def __str__(self):
        return "<Sandbox: %s at %s>" % (
            self.name,
            self.path,
        )

    def _mark_checked(self):
        """Sets the time of last check for update of the sandbox to now."""
        # We're assuming this is safe enough to be done under
        # a shared lock, as the check will eventually be re-done
        # under an exclusive lock.
        last_check_file = os.path.join(self.path, '.last_check')
        open(last_check_file, 'wb').write(str(int(time.time())).encode('utf-8'))

    def _should_install_sandbox(self):
        """Checks if the sandbox is correctly installed.

        If the last check for update is older than `CHECK_INTERVAL`,
        checks if the sandbox should be updated.
        """
        if not os.path.isdir(self.path):
            return True

        try:
            fixups_file = os.path.join(self.path, '.fixups_applied')
            if not os.path.exists(fixups_file):
                return True
            current_fixups = set(open(fixups_file).read().split())
            if not current_fixups.issuperset(self.required_fixups):
                return True

            last_check_file = os.path.join(self.path, '.last_check')
            last_check = int(open(last_check_file, 'rb').read().decode())
            now_int = int(time.time())
            if last_check + CHECK_INTERVAL > now_int:
                return False

            ft_path = _filetracker_path(self.name)
            ft_client = ft.instance()
            expected_hash = ft_client.file_version(ft_path)
            if not expected_hash:
                raise SandboxError(
                    "Server did not return hash for "
                    "the sandbox image '%s'" % self.name
                )
            expected_hash = str(expected_hash)

            hash_file = os.path.join(self.path, '.hash')
            if not os.path.exists(hash_file):
                return True
            hash = open(hash_file, 'rb').read().strip()
            logger.debug("Comparing hashes: %s vs %s.", expected_hash, hash)
            if hash != expected_hash:
                return True

            # Last check file is updated only after the actual check
            # confirmed that we are up to date.
            self._mark_checked()
            return False

        except Exception:
            logger.warning("Failed to check if sandbox is up-to-date", exc_info=True)
            if os.path.isdir(self.path):
                # If something fails, but we have the sandbox itself, better do
                # not try to download it again.
                self._mark_checked()
                return False
            return True

    def _parse_last_modified(self, response):
        last_modified = response.info().get('last-modified')
        if last_modified:
            last_modified = email.utils.parsedate_tz(last_modified)
            last_modified = int(email.utils.mktime_tz(last_modified))
        return last_modified

    def _apply_fixups(self):
        """Applies fixups for the sandbox.

        We currently have only one fixup: `elf_loader_patch`. For more
        information about it see elf_loader_patch.py file.
        """
        operative = {}
        if 'elf_loader_patch' in self.required_fixups:
            operative['elf_loader_patch'] = _patch_elf_loader(self.path)

        fixups_file = os.path.join(self.path, '.fixups_applied')
        open(fixups_file, 'w').write('\n'.join(self.required_fixups))

        operatives_file = os.path.join(self.path, '.fixups_operative')
        open(operatives_file, 'w').write(
            '\n'.join([fixup for fixup in operative if operative[fixup]])
        )

    def has_fixup(self, name):
        """This function check whether the sandbox has applied the
        fixup with given name."""
        if not hasattr(self, 'operative_fixups'):
            operatives_file = os.path.join(self.path, '.fixups_operative')
            self.operative_fixups = open(operatives_file).read().split('\n')

        return name in self.operative_fixups

    def _get(self):
        """Downloads and installs the sandbox if it is not installed correctly
        or should be updated.

        This function has a bug which causes that simultaneous download
        of the same sandbox is possible and this causes an error.
        The bug is that we are deleting whole sandbox directory before
        we start downloading the sandbox thus we are deleting
        the `.lock` file inside that directory.
        """
        name = self.name
        path = self.path

        logger.debug("Sandbox '%s' requested", name)

        self.file_lock.lock_shared()

        if not self._should_install_sandbox():
            # Sandbox is ready, so we return and *maintain* the file lock
            # for the lifetime of this object.
            return

        self.file_lock.unlock()
        self.file_lock.lock_exclusive()

        if not self._should_install_sandbox():
            self.file_lock.lock_shared()
            return

        try:
            logger.info("Downloading sandbox '%s' ...", name)

            if os.path.exists(path):
                rmtree(path)

            archive_path = path + '.tar.gz'

            try:
                ft_path = _filetracker_path(name)
                ft_client = ft.instance()
                vname = ft_client.get_file(ft_path, archive_path)
                version = ft_client.file_version(vname)
            except Exception:
                logger.warning(
                    "Failed to download sandbox from filetracker", exc_info=True
                )
                if SANDBOXES_URL:
                    url = SANDBOXES_URL + '/' + _urllib_path(name)
                    logger.info("  trying url: %s", url)
                    local_f = open(archive_path, 'wb')
                    try:
                        http_f = six.moves.urllib.request.urlopen(url)
                        shutil.copyfileobj(http_f, local_f)
                        local_f.close()
                    except:
                        os.unlink(archive_path)
                        raise
                    version = self._parse_last_modified(http_f)
                else:
                    raise SandboxError("Could not download sandbox '%s'" % (name,))

            logger.info(" extracting ...")

            tar = tarfile.open(archive_path, 'r')
            tar.extractall(SANDBOXES_BASEDIR)
            os.unlink(archive_path)

            if not os.path.isdir(path):
                raise SandboxError(
                    "Downloaded sandbox archive "
                    "did not contain expected directory '%s'" % name
                )

            self._apply_fixups()

            hash_file = os.path.join(path, '.hash')
            open(hash_file, 'wb').write(six.ensure_binary(str(version)))

            self._mark_checked()
            logger.info(" done.")

        except:
            self.file_lock.unlock()
            raise

        self.file_lock.lock_shared()


def get_sandbox(name):
    """Constructs a :class:`Sandbox` with the given ``name``.

    If a :class:`Sandbox` instance for the given ``name`` is already
    created, returns that instance.

    Only this function should be used to creating or getting
    :class:`Sandbox` instances.
    """
    return Sandbox._instance(name)


class NullSandbox(object):
    """A dummy sandbox doing nothing."""

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def __nonzero__(self):
        return False

    @property
    def path(self):
        raise AssertionError('NullSandbox has no path')


if __name__ == '__main__':
    import sys

    with get_sandbox(sys.argv[1]) as sandbox:
        print(sandbox.path)
