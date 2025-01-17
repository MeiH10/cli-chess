# Copyright (C) 2021-2023 Trevor Bayless <trevorbayless1@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import argparse
from cli_chess.__metadata__ import __name__, __version__, __description__
from cli_chess.utils.logging import log, redact_from_logs
from cli_chess.utils.config import get_config_path
from cli_chess.core.api import required_token_scopes


class ArgumentParser(argparse.ArgumentParser):
    """The main ArgumentParser class (inherits argparse.ArgumentParser).
       This allows for parsed arguments strings to be added to the log
       redactor in order to safely log parsed arguments (e.g. redacting API keys)
    """
    def parse_args(self, args=None, namespace=None):
        """Override default parse_args method to allow for parsed
           arguments to be added to the log redactor
        """
        arguments = super().parse_args(args, namespace)
        if arguments.token:
            redact_from_logs(arguments.token)

        log.debug(f"Parsed arguments: {arguments}")
        return arguments


def setup_argparse() -> ArgumentParser:
    """Sets up argparse and parses the arguments passed in at startup"""
    parser = ArgumentParser(description=f"{__name__}: {__description__}")
    parser.add_argument(
        "--token",
        metavar="API_TOKEN",
        type=str, help=f"Links your Lichess API token with cli-chess. Scopes required: {required_token_scopes}"
    )
    parser.add_argument(
        "--reset-config",
        help="Force resets the cli-chess configuration. Reverts the program to its default state.",
        action="store_true"
    )
    parser.add_argument(
        "-v", "--version",
        action="version",
        version=f"cli-chess v{__version__}",
    )

    debug_group = parser.add_argument_group("debugging")
    debug_group.description = f"Program settings and logs can be found here: {get_config_path()}"
    debug_group.add_argument(
        "--print-config",
        help="Prints the cli-chess configuration file to the terminal and exits.",
        action="store_true"
    )

    return parser
