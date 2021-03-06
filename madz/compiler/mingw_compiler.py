import os

from .gnu_compiler_base import GnuCompilerBase

from ..config import *

class MingwCompiler(GnuCompilerBase):

    @property
    def name(self):
        return "mingw"

    @property
    def supported_languages(self):
        return ["c", "cpp"]

    @property
    def available():
        try:
            ret, out, err = self.invoke_simple(["gcc", "--version"])
            return ret == 0
        except:
            return False

    @classmethod
    def _format_static_library(cls, libname):
        if libname.endswith(".lib"):
            libname = libname[:-4]
        return libname

    def sourcefile_to_objectfile(self, compile_file):
        return compile_file.with_extension("obj").fullname()

    def binaryname_compiler(self, plugin_stub, language):
        return {
            "c": "gcc",
            "cpp": "g++",
        }[language.name]

    def compiler_flags_base(self, plugin_stub, language):
        return (
            # Basic Config Flags
            (["-O0"] if (config.get(OptionCompilerDebug, 0.0) > 0.5) else ["-O4"]) +
            (["-g"] if (bool(config.get(OptionCompilerDebug, 0.0))) else []) +
            # Platform Compiler Flags
            (["-DMS_WIN64"] if config_target.get(OptionPlatformProcessorFamily) == "x86_64" else []) +
            # Language Compiler Flags
            ({
                "c": ["-std=c11", "-xc"],
                "cpp": ["-std=c++11", "-xc++"],
            }[language.name]) +
            # Include Directories
            ["-I"+str(language.wrap_directory)] + list(self._gen_header_include_dirs()) +
            # Linker Prep (position independant code and visibility)
            ["-fvisibility=hidden"] +
            #["-fpic"] + # Not needed for some MinGW compilers?
            # Warnings
            ["-Wall"])

    def compiler_flags_file(self, plugin_stub, language, compile_file):
        return ["-c", compile_file.path, "-o", self.sourcefile_to_objectfile(compile_file)]

    def binaryname_linker(self, plugin_stub, language):
        return self.binaryname_compiler(plugin_stub, language)

    def linker_flags_base(self, plugin_stub, language):
        return (
            # Basic Linker Flags
            ["-shared"] +
            ["-mwindows"] +
            # Language Linker Flags
            ({
                "c": [],
                "cpp": [],
            }[language.name]) +
            # Library Directories
            list(self._gen_link_library_dirs()) +
            # Warnings
            ["-Wl,--warn-unresolved-symbols"])

    def linker_flags_files(self, plugin_stub, language, source_files):
        return ["-o", str(language.get_output_file())] + \
            list(map(self.sourcefile_to_objectfile, source_files))

    def linker_flags_libraries(self, plugin_stub, language):
        return (list(map(lambda m: "{}".format(m), self._gen_link_library_statics())) * 2)

    def process_output(self, name, retcode, output, errput, foutput, ferrput):
        if retcode != 0:
            if output != "":
                logger.error(foutput)
            if errput != "":
                logger.error(ferrput)
        else:
            if output != "":
                logger.warning(foutput)
            if errput != "":
                logger.warning(ferrput)

        return retcode == 0
