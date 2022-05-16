import logging
import os
import pkg_resources
import platform
try:
    import queue
except ImportError:
    import Queue as queue
import re
import subprocess
import six
import sys
import threading
if sys.version_info < (3, ):
    from ConfigParser import RawConfigParser
else:
    from configparser import RawConfigParser


logger = logging.getLogger("mxdev")


def print_stderr(s):
    sys.stderr.write(s)
    sys.stderr.write('\n')
    sys.stderr.flush()


try:
    advance_iterator = next
except NameError:
    def advance_iterator(it):
        return it.next()

try:
    raw_input = raw_input
except NameError:
    raw_input = input


# shameless copy from
# http://stackoverflow.com/questions/377017/test-if-executable-exists-in-python
def which(name_root, default=None):
    def is_exe(fpath):
        return os.path.exists(fpath) and os.access(fpath, os.X_OK)

    if platform.system() == 'Windows':
        # http://www.voidspace.org.uk/python/articles/command_line.shtml#pathext
        pathext = os.environ['PATHEXT']
        # example: ['.py', '.pyc', '.pyo', '.pyw', '.COM', '.EXE', '.BAT', '.CMD']
        names = [name_root + ext for ext in pathext.split(';')]
    else:
        names = [name_root]

    for name in names:
        for path in os.environ["PATH"].split(os.pathsep):
            exe_file = os.path.join(path, name)
            if is_exe(exe_file):
                return exe_file

    if default is not None:
        return default

    logger.error("Cannot find executable %s in PATH", name_root)
    sys.exit(1)


def version_sorted(inp, *args, **kwargs):
    """
    Sorts components versions, it means that numeric parts of version
    treats as numeric and string as string.

    Eg.: version-1-0-1 < version-1-0-2 < version-1-0-10
    """
    num_reg = re.compile(r'([0-9]+)')

    def int_str(val):
        try:
            return int(val)
        except ValueError:
            return val

    def split_item(item):
        return tuple([int_str(j) for j in num_reg.split(item)])

    def join_item(item):
        return ''.join([str(j) for j in item])

    output = [split_item(i) for i in inp]
    return [join_item(i) for i in sorted(output, *args, **kwargs)]


def memoize(f, _marker=[]):
    def g(*args, **kwargs):
        name = '_memoize_%s' % f.__name__
        value = getattr(args[0], name, _marker)
        if value is _marker:
            value = f(*args, **kwargs)
            setattr(args[0], name, value)
        return value
    return g


class WCError(Exception):
    """ A working copy error. """


class BaseWorkingCopy(object):
    def __init__(self, source):
        self._output = []
        self.output = self._output.append
        self.source = source

    def should_update(self, **kwargs):
        offline = kwargs.get('offline', False)
        if offline:
            return False
        update = self.source.get('update', kwargs.get('update', False))
        if not isinstance(update, bool):
            if update.lower() in ('true', 'yes'):
                update = True
            elif update.lower() in ('false', 'no'):
                update = False
            else:
                raise ValueError("Unknown value for 'update': %s" % update)
        return update


def yesno(question, default=True, all=True):
    if default:
        question = "%s [Yes/no" % question
        answers = {
            False: ('n', 'no'),
            True: ('', 'y', 'yes'),
        }
    else:
        question = "%s [yes/No" % question
        answers = {
            False: ('', 'n', 'no'),
            True: ('y', 'yes'),
        }
    if all:
        answers['all'] = ('a', 'all')
        question = "%s/all] " % question
    else:
        question = "%s] " % question
    while 1:
        answer = raw_input(question).lower()
        for option in answers:
            if answer in answers[option]:
                return option
        if all:
            print_stderr("You have to answer with y, yes, n, no, a or all.")
        else:
            print_stderr("You have to answer with y, yes, n or no.")


main_lock = input_lock = output_lock = threading.RLock()


def worker(working_copies, the_queue):
    while True:
        if working_copies.errors:
            return
        try:
            wc, action, kwargs = the_queue.get_nowait()
        except queue.Empty:
            return
        try:
            output = action(**kwargs)
        except WCError:
            output_lock.acquire()
            for lvl, msg in wc._output:
                lvl(msg)
            for line in sys.exc_info()[1].args[0].split('\n'):
                logger.error(line)
            working_copies.errors = True
            output_lock.release()
        else:
            output_lock.acquire()
            for lvl, msg in wc._output:
                lvl(msg)
            if kwargs.get('verbose', False) and output is not None and output.strip():
                if six.PY3 and isinstance(output, six.binary_type):
                    output = output.decode('utf8')
                print(output)
            output_lock.release()


_workingcopytypes = None


def get_workingcopytypes():
    global _workingcopytypes
    if _workingcopytypes is not None:
        return _workingcopytypes
    group = 'mxdev.workingcopytypes'
    _workingcopytypes = {}
    addons = {}
    for entrypoint in pkg_resources.iter_entry_points(group=group):
        key = entrypoint.name
        workingcopytype = entrypoint.load()
        if entrypoint.dist.project_name == 'mxdev':
            _workingcopytypes[key] = workingcopytype
        else:
            if key in addons:
                logger.error("There already is a working copy type addon registered for '%s'.", key)
                sys.exit(1)
            logger.info("Overwriting '%s' with addon from '%s'.", key, entrypoint.dist.project_name)
            addons[key] = workingcopytype
    _workingcopytypes.update(addons)
    return _workingcopytypes


class WorkingCopies(object):
    def __init__(self, sources, threads=5):
        self.sources = sources
        self.threads = threads
        self.errors = False
        self.workingcopytypes = get_workingcopytypes()

    def process(self, the_queue):
        if self.threads < 2:
            worker(self, the_queue)
        else:
            if sys.version_info < (2, 6):
                # work around a race condition in subprocess
                _old_subprocess_cleanup = subprocess._cleanup

                def _cleanup():
                    pass

                subprocess._cleanup = _cleanup

            threads = []

            for i in range(self.threads):
                thread = threading.Thread(target=worker, args=(self, the_queue))
                thread.start()
                threads.append(thread)
            for thread in threads:
                thread.join()
            if sys.version_info < (2, 6):
                subprocess._cleanup = _old_subprocess_cleanup
                subprocess._cleanup()

        if self.errors:
            logger.error("There have been errors, see messages above.")
            sys.exit(1)

    def checkout(self, packages, **kwargs):
        the_queue = queue.Queue()
        if 'update' in kwargs:
            if isinstance(kwargs['update'], bool):
                pass
            elif kwargs['update'].lower() in ('true', 'yes', 'on', 'force'):
                if kwargs['update'].lower() == 'force':
                    kwargs['force'] = True
                kwargs['update'] = True
            elif kwargs['update'].lower() in ('false', 'no', 'off'):
                kwargs['update'] = False
            else:
                logger.error("Unknown value '%s' for always-checkout option." % kwargs['update'])
                sys.exit(1)
        kwargs.setdefault('submodules', 'always')
        if kwargs['submodules'] in ['always', 'never', 'checkout']:
            pass
        else:
            logger.error("Unknown value '%s' for update-git-submodules option." % kwargs['submodules'])
            sys.exit(1)
        for name in packages:
            kw = kwargs.copy()
            if name not in self.sources:
                logger.error("Checkout failed. No source defined for '%s'." % name)
                sys.exit(1)
            source = self.sources[name]
            vcs = source['vcs']
            wc = self.workingcopytypes.get(vcs)(source)
            if wc is None:
                logger.error("Unknown repository type '%s'." % vcs)
                sys.exit(1)
            update = wc.should_update(**kwargs)
            if not os.path.exists(source['path']):
                pass
            elif os.path.islink(source['path']):
                logger.info("Skipped update of linked '%s'." % name)
                continue
            elif update and wc.status() != 'clean' and not kw.get('force', False):
                print_stderr("The package '%s' is dirty." % name)
                answer = yesno("Do you want to update it anyway?", default=False, all=True)
                if answer:
                    kw['force'] = True
                    if answer == 'all':
                        kwargs['force'] = True
                else:
                    logger.info("Skipped update of '%s'." % name)
                    continue
            logger.info("Queued '%s' for checkout.", name)
            the_queue.put_nowait((wc, wc.checkout, kw))
        self.process(the_queue)

    def matches(self, source):
        name = source['name']
        if name not in self.sources:
            logger.error("Checkout failed. No source defined for '%s'." % name)
            sys.exit(1)
        source = self.sources[name]
        try:
            vcs = source['vcs']
            wc = self.workingcopytypes.get(vcs)(source)
            if wc is None:
                logger.error("Unknown repository type '%s'." % vcs)
                sys.exit(1)
            return wc.matches()
        except WCError:
            for line in sys.exc_info()[1].args[0].split('\n'):
                logger.error(line)
            sys.exit(1)

    def status(self, source, **kwargs):
        name = source['name']
        if name not in self.sources:
            logger.error("Status failed. No source defined for '%s'." % name)
            sys.exit(1)
        source = self.sources[name]
        try:
            vcs = source['vcs']
            wc = self.workingcopytypes.get(vcs)(source)
            if wc is None:
                logger.error("Unknown repository type '%s'." % vcs)
                sys.exit(1)
            return wc.status(**kwargs)
        except WCError:
            for line in sys.exc_info()[1].args[0].split('\n'):
                logger.error(line)
            sys.exit(1)

    def update(self, packages, **kwargs):
        the_queue = queue.Queue()
        for name in packages:
            kw = kwargs.copy()
            if name not in self.sources:
                continue
            source = self.sources[name]
            vcs = source['vcs']
            wc = self.workingcopytypes.get(vcs)(source)
            if wc is None:
                logger.error("Unknown repository type '%s'." % vcs)
                sys.exit(1)
            if wc.status() != 'clean' and not kw.get('force', False):
                print_stderr("The package '%s' is dirty." % name)
                answer = yesno("Do you want to update it anyway?", default=False, all=True)
                if answer:
                    kw['force'] = True
                    if answer == 'all':
                        kwargs['force'] = True
                else:
                    logger.info("Skipped update of '%s'." % name)
                    continue
            logger.info("Queued '%s' for update.", name)
            the_queue.put_nowait((wc, wc.update, kw))
        self.process(the_queue)


class Rewrite(object):
    _matcher = re.compile(r"(?P<option>^\w+) (?P<operator>[~=]{1,2}) (?P<value>.+)$")

    def _iter_prog_lines(self, prog):
        for line in prog.split('\n'):
            line = line.strip()
            if line:
                yield line

    def __init__(self, prog):
        self.rewrites = {}
        lines = self._iter_prog_lines(prog)
        for line in lines:
            match = self._matcher.match(line)
            matchdict = match.groupdict()
            option = matchdict['option']
            if option in ('name', 'path'):
                raise ValueError("Option '%s' not allowed in rewrite:\n%s" % (option, prog))
            operator = matchdict['operator']
            rewrites = self.rewrites.setdefault(option, [])
            if operator == '~':
                try:
                    substitute = advance_iterator(lines)
                except StopIteration:
                    raise ValueError("Missing substitution for option '%s' in rewrite:\n%s" % (option, prog))
                rewrites.append(
                    (operator, re.compile(matchdict['value']), substitute))
            elif operator == '=':
                rewrites.append(
                    (operator, matchdict['value']))
            elif operator == '~=':
                rewrites.append(
                    (operator, re.compile(matchdict['value'])))

    def __call__(self, source):
        for option, operations in self.rewrites.items():
            for operation in operations:
                operator = operation[0]
                if operator == '~':
                    if operation[1].search(source.get(option, '')) is None:
                        return
                elif operator == '=':
                    if operation[1] != source.get(option, ''):
                        return
                elif operator == '~=':
                    if operation[1].search(source.get(option, '')) is None:
                        return
        for option, operations in self.rewrites.items():
            for operation in operations:
                operator = operation[0]
                if operator == '~':
                    orig = source.get(option, '')
                    source[option] = operation[1].sub(operation[2], orig)
                    if source[option] != orig:
                        logger.debug("Rewrote option '%s' from '%s' to '%s'." % (option, orig, source[option]))


class LegacyRewrite(Rewrite):
    def __init__(self, prefix, substitution):
        Rewrite.__init__(self, "url ~ ^%s\n%s" % (prefix, substitution))
