import sys
import os
import threading
import queue
import time
import subprocess
import logging
import traceback

logger = logging.getLogger(__name__)

import zmq

from madz.bootstrap import *
from madz.config import *
from ...IMinion import IMinion
from ...Daemon import Daemon

class ExecuterMinionSubprocess(object):

    def __init__(self, minion):
        self._minion = minion._minion

        self.bootstrap_port = Daemon.next_minion_port()
        self.control_port = Daemon.next_minion_port()

        self._bind_str = "tcp://127.0.0.1:{port}".format(port=self.bootstrap_port)
        self._proc_bootstrapper = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "executer_bootstrap.py"))

        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PAIR)
        self.socket.bind(self._bind_str)

    def banish(self):
        pass

    def execute(self, argv, userconfig):
        system = Daemon.current.system

        with config.and_merge(system.config):
            with config.and_merge(userconfig):
                system.index()

                execute_plugin_name = argv[0] if len(argv) > 0 else config.get(OptionSystemExecutePlugin)
                execute_function_name = argv[1] if len(argv) > 1 else config.get(OptionSystemExecuteFunctionName)

                if execute_plugin_name is None:
                    logger.error("DAEMON[{}] cannot execute. OptionSystemExecutePlugin is not defined.".format(self._minion.identity()))
                    return

                plugin_stub = system.resolve_plugin(execute_plugin_name)

                if(plugin_stub.executable == False):
                    logger.error("DAEMON[{}] cannot execute {}. executable flag not set to True.".format(self._minion.identity(), plugin_stub.id.namespace))
                    return

                logger.debug("DAEMON[{}] Loading plugins for '{}' targeting function '{}'.".format(
                        self._minion.identity(),
                        execute_plugin_name,
                        execute_function_name
                    ))
                self.load(plugin_stub)

                logger.info("DAEMON[{}] Calling function '{}' from plugin '{}'.".format(self._minion.identity(), execute_function_name, execute_plugin_name))
                self.call_func(plugin_stub, execute_function_name)

                logger.info("DAEMON[{}] Completed, new instance started!".format(self._minion.identity()))


    @staticmethod
    def _unique(seq):
        seen = set()
        for x in seq:
            if x in seen:
                continue
            seen.add(x)
            yield x

    @staticmethod
    def _gen_load_pattern(plugin_stub, until="final", memo=[], skip=[]):
        # base:
        res = []

        # get into memory:
        res += [("in-mem", plugin_stub, [])]
        if until == "in-mem":
            return res

        # init:
        depends = plugin_stub.gen_recursive_loaded_depends()
        res += [load_pattern for require in depends for load_pattern in ExecuterMinionSubprocess._gen_load_pattern(require, "inited")]
        res += [("inited", plugin_stub, depends)]
        if until == "inited":
            return res

        # final
        if plugin_stub in skip:
            return res
        imports = list(filter(lambda p: p not in depends, plugin_stub.gen_required_loaded_imports()))
        res += [load_pattern for require in imports for load_pattern in ExecuterMinionSubprocess._gen_load_pattern(require, "final", memo + imports, memo)]
        res += [("final", plugin_stub, imports)]
        if until == "final":
            return res

    def load(self, plugin_stub):
        for p in ExecuterMinionSubprocess._unique(
            map(lambda e: (
                    "load-artifact",
                    e[0],
                    e[1].output_file_location().path,
                    tuple(map(lambda p: p.output_file_location().path, e[2]))),
                ExecuterMinionSubprocess._gen_load_pattern(plugin_stub))):
            # Cleanup object for sending:
            sending = p

            while True:
                try:
                    self.socket.send_pyobj(sending, zmq.NOBLOCK)
                    break
                except zmq.ZMQError:
                    if self._minion.banished:
                        raise Exception()
                    continue

            while True:
                try:
                    res = self.socket.recv_pyobj(zmq.NOBLOCK)
                    break
                except zmq.ZMQError:
                    if self._minion.banished:
                        raise Exception()
                    continue

            # Executer responded with traceback
            if (isinstance(res, str)):
                logger.error("DAEMON[{}] Encountered problem loading {}:\n\t{}".format(self.identity(), plugin_stub, res))
                raise Exception("Encountered problem loading {}!".format(plugin_stub))


    def call_func(self, plugin_stub, func):
        index = plugin_stub.get_function_index(func)
        self.socket.send_pyobj(("execute", plugin_stub.output_file_location().path, index))

        self.socket.close()
        self.context.term()

class ExecuteControlThread(threading.Thread):
    def __init__(self, minion):
        super().__init__()
        self._minion = minion

    def run(self):
        context = zmq.Context()
        socket = context.socket(zmq.REP)
        socket.bind("tcp://127.0.0.1:{port}".format(port=self._minion.port))

        while not self._minion.banished:
            try:
                command = socket.recv_pyobj(zmq.NOBLOCK)
            except zmq.ZMQError:
                time.sleep(0.1)
                continue
            report = None
            try:
                #TODO: set up logging report
                logger.info("DAEMON[{}] Starting execute of '{}'.".format(self._minion.identity(), " ".join(command[0])))

                subproc = ExecuterMinionSubprocess(self)
                self._minion.subprocs.append(subproc)

                socket.send_pyobj((subproc.bootstrap_port,))

                time.sleep(0.01)

                subproc.execute(*command)
            except Exception as e:
                tb_string = "\n\t".join(("".join(traceback.format_exception(*sys.exc_info()))).split("\n"))
                logger.error("DAEMON[{}] Failed on execute of '{}':\n\t{}".format(self._minion.identity(), " ".join(command[0]), tb_string))

@bootstrap_plugin("madz.minion.Executer")
class ExecuterMinion(IMinion):
    current = None

    def __init__(self):
        self.banished = False
        self.spawned = False
        self.subprocs = []
        self._thread = ExecuteControlThread(self)
        self.port = Daemon.next_minion_port()

    @classmethod
    def spawn(cls):
        if (cls.current is None):
            cls.current = ExecuterMinion()
        return cls.current._spawn()

    def _spawn(self):
        if not (self.spawned):
            self.spawned = True
            self._thread.start()
        return (self, [self.port])

    def banish(self):
        self.banished = True
        for subproc in self.subprocs:
            subproc.banish()
        self._thread.join()

    @classmethod
    def identity(cls):
        return "execute"

