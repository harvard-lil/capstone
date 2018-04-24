from distutils.sysconfig import get_python_lib
import inspect

from django.db.backends import utils


python_lib_path = get_python_lib()

class TracingDebugWrapper(utils.CursorDebugWrapper):
    def log_message(self, message):
        utils.logger.debug(message)

    def get_userland_stack_frame(self, stack):
        try:
            return next(x for x in stack[2:] if not x.filename.startswith(python_lib_path))
        except StopIteration:
            return None

    def capture_stack(self):
        stack = inspect.stack()
        userland_stack_frame = self.get_userland_stack_frame(stack)

        self.db.queries_log[-1].update({
            'stack': stack,
            'userland_stack_frame': userland_stack_frame,
        })

        if userland_stack_frame:
            self.log_message("Previous SQL query called by %s:%s:\n%s" % (
                userland_stack_frame.filename,
                userland_stack_frame.lineno,
                userland_stack_frame.code_context[0].rstrip()))

    def execute(self, *args, **kwargs):
        try:
            return super().execute(*args, **kwargs)
        finally:
            self.capture_stack()

    def executemany(self, *args, **kwargs):
        try:
            return super().executemany(*args, **kwargs)
        finally:
            self.capture_stack()