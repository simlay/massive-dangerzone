from madz.stub import *

plugin = Plugin(
    name="base_c.c",
    version="1.0.0",

    language="python",
    description=[
                 TypeDeclaration("Color",
            TypeStruct({
                "r" : TypeInt8,
                "g" : TypeInt8,
                "b" : TypeInt8
            }), doc="A Color in 3R"),
        VariableDefinition("origin_distance",
            TypeFunction(
                TypeFloat32,
                [TypeFunctionArgument("x", TypeFloat32),
                 TypeFunctionArgument("y", TypeFloat32)]))
    ])
