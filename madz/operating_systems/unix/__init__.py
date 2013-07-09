import ctypes
import os

import logging

logger = logging.getLogger(__name__)

class UnixOperatingSystem(object):
    def __init__(self):
        self.loadedinit_plugins = {}
        self.loadedimports_plugins = {}

    @staticmethod
    def output_file_location(plugin_stub):
        return os.path.join(plugin_stub.directory, ".output", plugin_stub.id.namespace + ".madz")

    def load_init(self, plugin_stub):
        """Performs the first phase of loading a plugin.

        Initializes the plugin with it's dependencies.

        """
        if plugin_stub in self.loadedinit_plugins:
            return

        logger.debug("LOADING: Opening plugin DLL: {}".format(plugin_stub))

        plugin_dll = ctypes.cdll.LoadLibrary(self.output_file_location(plugin_stub))
        
        madz_init = getattr(plugin_dll, "___madz_EXTERN_INIT")
        madz_init.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p)]

        return_pointer = ctypes.pointer(ctypes.c_void_p())

        language_loader = plugin_stub.language.make_loader()

        depends = plugin_stub.gen_recursive_loaded_depends()
        depends_array = (ctypes.c_void_p * len(depends))()

        for i, dep in enumerate(depends):
            depends_array[i] = self.loadedinit_plugins[dep][1]

        logger.debug("LOADING: Initializing plugin: {}".format(plugin_stub))

        language_loader.pre_init(self, plugin_dll)
        error_val = madz_init(depends_array, return_pointer)
        language_loader.post_init(self, plugin_dll)

        self.loadedinit_plugins[plugin_stub] = (plugin_dll, return_pointer.contents)

    def load_imports(self, plugin_stub):
        """Performs the second phase of loading a plugin.

        Intializes the plugin by passing it it's imports.

        """
        if plugin_stub in self.loadedimports_plugins:
            return

        plugin_dll, plugin_pointer = self.loadedinit_plugins[plugin_stub]

        madz_initimports = getattr(plugin_dll, "___madz_EXTERN_INITIMPORTS")
        madz_initimports.argtypes = [ctypes.POINTER(ctypes.c_void_p)]

        language_loader = plugin_stub.language.make_loader()

        imports = plugin_stub.loaded_imports
        imports_array = (ctypes.c_void_p * len(imports))()

        for i, imp in enumerate(imports):
            imports_array[i] = self.loadedinit_plugins[imp][1]

        logger.debug("LOADING: Initializing plugin imports: {}".format(plugin_stub))

        error_val = madz_initimports(imports_array)
        language_loader.post_initimports(self, plugin_dll)

        self.loadedimports_plugins[plugin_stub] = (plugin_dll, plugin_pointer)

    def is_loaded_init(self, plugin_stub):
        """Returns true iff load_init has been called."""
        return plugin_stub in self.loaded_plugins

    def is_loaded_imports(self, plugin_stub):
        """Returns true iff load_imports has been called."""
        return plugin_stub in self.loadedimports_plugins

    def is_loaded(self, plugin_stub):
        """Returns true iff the plugin has been completely loaded.."""
        return self.is_loaded_init(plugin_stub) and self.is_loaded_imports(plugin_stub)

    def load(self, plugin_stub, recur=True):
        for dep in plugin_stub.gen_recursive_loaded_depends():
            self.load_init(dep)

        self.load_init(plugin_stub)

        for imp in plugin_stub.loaded_imports:
            self.load_init(imp)

        self.load_imports(plugin_stub)

