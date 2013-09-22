"""Support functions for pyxmpp2 test suite."""

import os
import sys
import logging
import unittest

TEST_DIR = os.path.dirname(__file__)
DATA_DIR = os.path.join(TEST_DIR, "data")

RESOURCES = ['network', 'lo-network', 'gsasl']

if "TEST_USE" in os.environ:
    RESOURCES = os.environ["TEST_USE"].split()

if "TEST_STACKDUMP_FILE" in os.environ:
    import traceback
    import threading
    import time
    def stack_dumper():
        stackdump_file = open(os.environ.get("TEST_STACKDUMP_FILE"), "w")
        while True:
            time.sleep(5)
            stackdump_file.write(time.ctime() + "\n")
            frames = sys._current_frames()
            for frame in frames.values():
                traceback.print_stack(frame, file = stackdump_file)
            stackdump_file.write("\n")
            stackdump_file.flush()
    thr = threading.Thread(target = stack_dumper)
    thr.daemon = True
    thr.start()

# pylint: disable=W0602,C0103
logging_ready = False
def setup_logging():
    """Set up logging for the tests.

    Log level used depends on number of '-v' in sys.argv
    """
    # pylint: disable=W0603
    global logging_ready
    if logging_ready:
        return
    if sys.argv.count("-v") > 2:
        logging.basicConfig(level=logging.DEBUG)
    elif sys.argv.count("-v") == 2:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.ERROR)
    logging_ready = True

def filter_tests(suite):
    """Make a new TestSuite from `suite`, removing test classes
    with names starting with '_'."""
    result = unittest.TestSuite()
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            result.addTest(filter_tests(test))
        elif not test.__class__.__name__.startswith("_"):
            result.addTest(test)
    return result

def load_tests(loader, tests, pattern):
    """Use default test list, just remove the classes which names start with
    '_'."""
    # pylint: disable=W0613
    suite = filter_tests(tests)
    return suite

