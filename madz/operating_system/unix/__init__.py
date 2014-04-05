import ctypes
import os

from ...fileman import *

class UnixOperatingSystem(object):
    """Operating System object for plugin support on Unix based operating system.

    Arguments:
        loadedinit_plugins: Dictionary of plugins
        loadedimports_plugins: Dictionary of plugins
    """
    class ArtifactLoadState(object):
        def __init__(self, filename):
            self.filename = filename
            self.cdll = None
            self.pointer = None
            self.finalized = False

        @property
        def in_memory(self):
            return not (self.cdll is None)

        @property
        def inited(self):
            return not (self.pointer is None)

        def _key(self):
            return (filename,)

        def __str__(self):
            return os.path.basename(str(self.filename))

        def __hash__(self):
            return hash(self._key())

        def __eq__(self, other):
            return type(self) == type(other) and self._key() == other._key()

    def __init__(self):
        self.artifacts = {}

    def _ensure(self, artifact):
        if not (artifact in self.artifacts):
            self.artifacts[artifact] = UnixOperatingSystem.ArtifactLoadState(artifact)
        return self.artifacts[artifact]

    def load_memory(self, artifact):
        artifact = self._ensure(artifact)
        #if artifact.in_memory:
        #    print("Redundent load_memory call: {}".format(artifact))

        artifact.cdll = ctypes.cdll.LoadLibrary(str(artifact.filename))


    def load_init(self, artifact, requires):
        """Loads and calls init on an artifact (a .madz output file), passing it the dependencies,
        called requires, as generated by 'plugin_stub.gen_recursive_loaded_depends()'."""

        artifact = self._ensure(artifact)
        #if artifact.inited:
        #    print("Redundent load_init call: {}".format(artifact))

        depends = list(map(lambda r: self._ensure(r), requires))
        for d in depends:
            if not d.inited:
                raise Exception("ARTIFACT[{}] Dependent artifact '{}' not inited!".format(artifact, d))

        madz_init = getattr(artifact.cdll, "___madz_EXTERN_INIT")
        madz_init.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_void_p)]

        return_pointer = ctypes.pointer(ctypes.c_void_p())

        depends_array = (ctypes.c_void_p * len(depends))()
        for i, dep in enumerate(depends):
            depends_array[i] = dep.pointer

        error_val = madz_init(depends_array, return_pointer)

        artifact.pointer = return_pointer[0]


    def load_final(self, artifact, requires):
        """Loads and calls initimport on an artifact (a .madz output file). passing it the
        dependencies called requires as generated by:

        ```
        deps = plugin_stub.gen_recursive_loaded_depends()
        imports = list(filter(lambda p: p not in deps, plugin_stub.gen_required_loaded_imports()))
        ```
        """
        artifact = self._ensure(artifact)
        #if artifact.finalized:
        #    print("Redundent load_final call: {}".format(artifact))

        imports = list(map(lambda r: self._ensure(r), requires))
        for i in imports:
            if not i.inited:
                raise Exception("ARTIFACT[{}] Imported artifact '{}' not inited!".format(artifact, i))

        madz_initimports = getattr(artifact.cdll, "___madz_EXTERN_INITIMPORTS")
        madz_initimports.argtypes = [ctypes.POINTER(ctypes.c_void_p)]

        imports_array = (ctypes.c_void_p * len(imports))()

        for i, imp in enumerate(imports):
            imports_array[i] = imp.pointer

        error_val = madz_initimports(imports_array)
        artifact.finalized = True


    def get_function(self, artifact, index):
        """Returns a function pointer to a function from provided plugin with provided name.

        Args:
            artifact: The artifact directory/artifact_identity
            index: A function index. For example, like that found by plugin_stub.get_function_index()

        Returns:
            A function pointer
        """
        artifact = self._ensure(artifact)

        artifact_pointer_pointer_type = ctypes.POINTER(ctypes.c_void_p)

        func_pointer = ctypes.cast(artifact.pointer, artifact_pointer_pointer_type)[index]

        # assume () -> void
        return ctypes.CFUNCTYPE(None)(func_pointer)
