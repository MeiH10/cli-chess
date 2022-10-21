# Copyright (C) 2021-2022 Trevor Bayless <trevorbayless1@gmail.com>
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

from cli_chess.menus.vs_computer_menu import VsComputerMenuModel
from cli_chess.menus import MenuPresenter, MultiValueMenuView
from cli_chess.game.game_options import OfflineGameOptions
from cli_chess.game.offline import start_offline_game


class VsComputerMenuPresenter(MenuPresenter):
    """Defines the VsComputer menu"""
    def __init__(self, model: VsComputerMenuModel):
        self.model = model
        self.view = MultiValueMenuView(self, container_width=40, column_width=22)
        super().__init__(self.model, self.view)

    def handle_start_game(self) -> None:
        """Handle starting the game"""
        game_parameters = self._create_dict_of_selected_values()
        start_offline_game(game_parameters)

    def _create_dict_of_selected_values(self) -> dict:
        """Creates a dictionary of all selected values"""
        try:
            selections_dict = {}
            for index, menu_option in enumerate(self.get_menu_options()):
                selections_dict[f"{menu_option.option_name}"] = menu_option.selected_value['name']

            return OfflineGameOptions().transpose_selection_dict(selections_dict)
        except KeyError:
            # TODO: Print error to screen
            pass
