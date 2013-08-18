"""helper/arg_parser.py
@OffbyOneStudios 2013
Helper function for interpreting command line.
"""

import argparse
import logging

from ..config import *
from ..action import actions

logger = logging.getLogger(__name__)

def generate_parser(valid_commands):
    parser = argparse.ArgumentParser(description='Perform actions across a plugin system.')

    parser.add_argument("commands",
        action='store',
        nargs='+',
        choices=valid_commands,
        help="The command(s) to execute on the system, in order.")
    parser.add_argument("-m", "--modes",
        action='append',
        default=[],
        nargs='*',
        help="The modes to apply to the system before executing it."
        )
    parser.add_argument("-l", "--log-level")
    parser.add_argument("-p", "--plugins")

    return parser

def execute_args_across(argv, system, user_config):
    # Apply system and user config.
    with config.and_merge(system.config):
        with config.and_merge(user_config):
            # Build valid command list for arg parsing
            # We can't build modes because that would require us to apply the command config.
            valid_commands = list(map(lambda c: c.label, config.get_option_type(CommandConfig)))

            # Parse the arguments
            args = generate_parser(valid_commands).parse_args(argv[1:])

            # Expand out the parsed arguments
            parsed_commands = args.commands
            parsed_modes = args.modes

            # Apply Commands
            for parsed_command in parsed_commands:
                logger.debug("Starting command '{}'".format(parsed_command))
                with config.and_merge(config.get(CommandConfig.make_key(parsed_command))):
                    # Apply Modes
                    old_config_state = config.copy_state()
                    for parsed_mode in [item for sublist in parsed_modes for item in sublist]:
                        logger.debug("Enetering mode '{}'".format(parsed_mode))
                        # TODO: Check for non-existent ModeConfigs
                        config.add(config.get(ModeConfig.make_key(parsed_mode)))

                    # Do Actions
                    for action in config.get(OptionCommandActions):
                        actions[action](system).do()

                    # Remove Modes, safely cleanup config.
                    config.set_state(old_config_state)
