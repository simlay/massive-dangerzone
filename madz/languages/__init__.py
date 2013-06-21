import importlib

class LanguageError(Exception): pass
class LanguageDoesNotExistError(LanguageError): pass
class LanguageFeatureMissingError(LanguageError): pass

def get_wrapper_generator(language):
    #try:
    language_module = importlib.import_module("." + language, __name__)
    # TODO(Mason): Forward import errors.    
    #except ImportError:
    #    raise LanguageDoesNotExistError("Language does not exist: '{}'".format(language))

    try:
        gen_class = language_module.WrapperGenerator
    except AttributeError:
        raise LanguageFeatureMissingError("Language does not have a WrapperGenerator class: '{}'".format(language))

    return gen_class


def get_builder(language):
    try:
        language_module = importlib.import_module("." + language, __name__)
    except ImportError:
        raise LanguageDoesNotExistError("Language does not exist: '{}'".format(language))

    try:
        build_class = language_module.Builder
    except AttributeError:
        raise LanguageFeatureMissingError("Language does not have a Builder class: '{}'".format(language))

    return build_class

