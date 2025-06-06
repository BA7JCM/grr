#!/usr/bin/env python
"""Client utilities common to all platforms."""

import hashlib
import logging
import os
import platform
import shlex
import subprocess
import threading
import time
from typing import Optional

from grr_response_client.local import binary_whitelist
from grr_response_core import config
from grr_response_core.lib import constants
from grr_response_core.lib.rdfvalues import crypto as rdf_crypto


def HandleAlarm(process):
  try:
    logging.info("Killing child process due to timeout")
    process.kill()
  # There is a race condition here where the process terminates
  # just before it would be killed. We ignore the exception
  # in that case as the process is already gone.
  except OSError:
    pass


def Execute(
    cmd: str,
    args: list[str],
    time_limit: int = -1,
    bypass_allowlist: bool = False,
    cwd: Optional[str] = None,
) -> tuple[bytes, bytes, int, float]:
  """Executes commands on the client.

  This function is the only place where commands will be executed
  by the GRR client. This makes sure that all issued commands are compared to an
  allowlist and no malicious commands are issued on the client machine.

  Args:
    cmd: The command to be executed.
    args: List of arguments.
    time_limit: Time in seconds the process is allowed to run.
    bypass_allowlist: Allow execution of things that are not in the allowlist.
      Note that this should only ever be called on a binary that passes the
      VerifySignedBlob check.
    cwd: Current working directory for the command.

  Returns:
    A tuple of stdout, stderr, return value and time taken.
  """
  if not bypass_allowlist and not IsExecutionAllowed(cmd, args):
    # Allowlist doesn't contain this cmd/arg pair
    logging.info(
        "Execution disallowed by allowlist: %s %s.", cmd, " ".join(args)
    )
    return b"", b"Execution disallowed by allowlist.", -1, -1.0

  return _Execute(cmd, args, time_limit, cwd=cwd)


def _Execute(
    cmd: str,
    args: list[str],
    time_limit: int = -1,
    cwd: Optional[str] = None,
) -> tuple[bytes, bytes, int, float]:
  """Executes cmd."""
  run = [cmd]
  run.extend(args)
  env = os.environ.copy()

  # We clear `LD_LIBRARY_PATH` and `PYTHON_PATH` to force usage of system
  # libraries. Otherwise, e.g. if the agent is bundled using PyInstaller, it
  # is going to override this so that Python interpreter can work. See [1, 2]
  # for more details.
  #
  # pylint: disable=line-too-long
  # fmt: off
  # [1]: https://pyinstaller.org/en/stable/runtime-information.html#ld-library-path-libpath-considerations
  # [2]: https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#launching-external-programs-from-the-frozen-application
  # pylint: enable=line-too-long
  # fmt: on
  env.pop("LD_LIBRARY_PATH", None)
  env.pop("PYTHON_PATH", None)

  logging.info("Executing %s.", " ".join(run))

  p = subprocess.Popen(
      run,
      stdin=subprocess.PIPE,
      stdout=subprocess.PIPE,
      stderr=subprocess.PIPE,
      env=env,
      cwd=cwd,
  )

  alarm = None
  if time_limit > 0:
    alarm = threading.Timer(time_limit, HandleAlarm, (p,))
    alarm.daemon = True
    alarm.start()

  stdout, stderr, exit_status = b"", b"", -1
  start_time = time.time()
  try:
    stdout, stderr = p.communicate()
    exit_status = p.returncode
  except IOError:
    # If we end up here, the time limit was exceeded
    pass
  finally:
    if alarm:
      alarm.cancel()
      alarm.join()

  return (stdout, stderr, exit_status, time.time() - start_time)


def IsExecutionAllowed(
    cmd: str,
    args: list[str],
) -> bool:
  """Check if a binary and args are in the allowlist.

  Args:
    cmd: Canonical path to the binary.
    args: List of arguments to be passed to the binary.

  Returns:
    Bool, True if execution is allowed.

  These allowlists could also go in the platform specific client files
  client_utils_<platform>.py. We chose to leave them here instead of putting
  them in global arrays to discourage people coding other modules from adding
  new commands to the allowlist before running them.
  The idea is to have a single place that lists every command we can run during
  normal operation (obviously doesn't catch the special cases where we bypass
  the list).
  A deployment-specific list is also checked (see local/binary_whitelist.py).
  """
  allowed_commands = map(shlex.split, config.CONFIG["Client.allowed_commands"])
  allowed_commands = list(allowed_commands)
  if [cmd] + list(args) in allowed_commands:
    return True

  if platform.system() == "Windows":
    allowlist = [
        ("arp.exe", ["-a"]),
        ("cmd.exe", ["/C", "echo 1"]),
        ("driverquery.exe", ["/v"]),
        ("ipconfig.exe", ["/all"]),
        ("netsh.exe", ["advfirewall", "firewall", "show", "rule", "name=all"]),
        (
            "netsh.exe",
            ["advfirewall", "monitor", "show", "firewall", "rule", "name=all"],
        ),
        ("tasklist.exe", ["/SVC"]),
        ("tasklist.exe", ["/v"]),
    ]
  elif platform.system() == "Linux":
    allowlist = [
        ("/bin/df", []),
        ("/bin/echo", ["1"]),
        ("/bin/mount", []),
        ("/bin/rpm", ["-qa"]),
        (
            "/bin/rpm",
            [
                "--query",
                "--all",
            ],
        ),
        (
            "/bin/rpm",
            [
                "--query",
                "--all",
                "--queryformat",
                "%{NAME}|%{EPOCH}|%{VERSION}|%{RELEASE}|%{ARCH}|%{INSTALLTIME}|%{VENDOR}|%{SOURCERPM}\n",
            ],
        ),
        ("/bin/sleep", ["10"]),
        ("/opt/CrowdStrike/falconctl", ["-g", "--cid", "--aid"]),
        ("/sbin/auditctl", ["-l"]),
        ("/sbin/ifconfig", ["-a"]),
        ("/sbin/iptables", ["-L", "-n", "-v"]),
        ("/sbin/lsmod", []),
        (
            "/usr/bin/dpkg",
            [
                "--list",
            ],
        ),
        (
            "/usr/bin/dpkg-query",
            [
                "--show",
                "--showformat",
                "${Package}|${Version}|${Architecture}|${Source}|${binary:Synopsis}\n",
            ],
        ),
        ("/usr/bin/last", []),
        ("/usr/bin/who", []),
        ("/usr/bin/yum", ["list", "installed", "-q"]),
        ("/usr/bin/yum", ["repolist", "-v", "-q"]),
        ("/usr/sbin/arp", ["-a"]),
        ("/usr/sbin/dmidecode", ["-q"]),
        ("/usr/sbin/sshd", ["-T"]),
        # Container Runtimes
        ("/home/kubernetes/bin/crictl", ["ps", "-a", "-o", "json"]),
        ("/usr/bin/crictl", ["ps", "-a", "-o", "json"]),
        ("/usr/bin/ctr", ["namespaces", "list"]),
        ("/usr/bin/ctr", ["--namespace", "k8s.io", "containers", "list"]),
        ("/usr/bin/docker", ["ps", "-a", "--format", "json", "--no-trunc"]),
        (
            "/usr/sbin/chroot",
            [
                "/hostroot",
                "/home/kubernetes/bin/crictl",
                "ps",
                "-a",
                "-o",
                "json",
            ],
        ),
        (
            "/usr/sbin/chroot",
            ["/hostroot", "/usr/bin/crictl", "ps", "-a", "-o", "json"],
        ),
        (
            "/usr/sbin/chroot",
            ["/hostroot", "/usr/bin/ctr", "namespaces", "list"],
        ),
        (
            "/usr/sbin/chroot",
            [
                "/hostroot",
                "/usr/bin/ctr",
                "--namespace",
                "k8s.io",
                "containers",
                "list",
            ],
        ),
        (
            "/usr/sbin/chroot",
            [
                "/hostroot",
                "/usr/bin/docker",
                "ps",
                "-a",
                "--format",
                "json",
                "--no-trunc",
            ],
        ),
    ]
  elif platform.system() == "Darwin":
    allowlist = [
        ("/bin/echo", ["1"]),
        ("/bin/launchctl", ["unload", config.CONFIG["Client.plist_path"]]),
        ("/usr/bin/hdiutil", ["info"]),
        ("/usr/bin/last", []),
        ("/usr/bin/who", []),
        ("/usr/sbin/arp", ["-a"]),
        ("/usr/sbin/kextstat", []),
        ("/usr/sbin/system_profiler", ["-xml", "SPHardwareDataType"]),
        ("/Applications/Falcon.app/Contents/Resources/falconctl", ["stats"]),
    ]
  else:
    allowlist = []

  for allowed_cmd, allowed_args in allowlist:
    if cmd == allowed_cmd and args == allowed_args:
      return True

  # Check if allowlist is overridden in the local GRR installation.
  if binary_whitelist.IsExecutionWhitelisted(cmd, args):
    return True

  return False


class MultiHasher(object):
  """An utility class that is able to applies multiple hash algorithms.

  Objects that need to construct `Hash` object with multiple hash values need
  to apply multiple hash algorithms to the given data. This class removes some
  boilerplate associated with it and provides a readable API similar to the one
  exposed by Python's `hashlib` module.

  Args:
    algorithms: List of names of the algorithms from the `hashlib` module that
      need to be applied.
    progress: An (optional) progress callback called when hashing functions are
      applied to the data.
  """

  def __init__(self, algorithms=None, progress=None):
    if not algorithms:
      algorithms = ["md5", "sha1", "sha256"]

    self._hashers = {}
    for algorithm in algorithms:
      self._hashers[algorithm] = hashlib.new(algorithm)
    self._bytes_read = 0

    self._progress = progress

  def HashFilePath(self, path, byte_count):
    """Updates underlying hashers with file on a given path.

    Args:
      path: A path to the file that is going to be fed to the hashers.
      byte_count: A maximum numbers of bytes that are going to be processed.
    """
    with open(path, "rb") as fd:
      self.HashFile(fd, byte_count)

  def HashFile(self, fd, byte_count):
    """Updates underlying hashers with a given file.

    Args:
      fd: A file object that is going to be fed to the hashers.
      byte_count: A maximum number of bytes that are going to be processed.
    """
    while byte_count > 0:
      buf_size = min(byte_count, constants.CLIENT_MAX_BUFFER_SIZE)
      buf = fd.read(buf_size)
      if not buf:
        break

      self.HashBuffer(buf)
      byte_count -= buf_size

  def HashBuffer(self, buf):
    """Updates underlying hashers with a given buffer.

    Args:
      buf: A byte buffer (string object) that is going to be fed to the hashers.
    """
    for hasher in self._hashers.values():
      hasher.update(buf)
      if self._progress:
        self._progress()

    self._bytes_read += len(buf)

  def GetHashObject(self):
    """Returns a `Hash` object with appropriate fields filled-in."""
    hash_object = rdf_crypto.Hash()
    hash_object.num_bytes = self._bytes_read
    for algorithm in self._hashers:
      setattr(hash_object, algorithm, self._hashers[algorithm].digest())
    return hash_object
