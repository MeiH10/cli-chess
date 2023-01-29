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

from cli_chess.core.game import GameModelBase
from cli_chess.modules.game_options import GameOption
from cli_chess.core.api import IncomingEventManager, GameStream
from cli_chess.utils import log
from cli_chess.modules.token_manager import TokenManagerModel
from chess import Color, COLOR_NAMES, WHITE
from typing import Optional


class OnlineGameModel(GameModelBase):
    """This model must only be used for games owned by the linked lichess user.
       Games not owned by this account must directly use the base model instead.
    """
    def __init__(self, game_parameters: dict, iem: IncomingEventManager):
        # TODO: Send None here instead on random (need to update board model logic if so)?
        self.my_color: Color = game_parameters[GameOption.COLOR] if not "random" else WHITE
        super().__init__(variant=game_parameters[GameOption.VARIANT], orientation=self.my_color, fen=None)

        self._save_game_metadata(game_parameters=game_parameters)
        self.incoming_event_manager = iem
        self.game_stream = Optional[GameStream]

        self.incoming_event_manager.e_new_event_received.add_listener(self.handle_iem_event)

    def start_ai_challenge(self) -> None:
        # TODO: This should probably be pushed over to the GameStream to handle
        client = TokenManagerModel().get_validated_client()
        client.challenges.create_ai(level=self.game_metadata['ai_level'],
                                    clock_limit=self.game_metadata['clock']['white']['time'],
                                    clock_increment=self.game_metadata['clock']['white']['increment'],
                                    color=self.game_metadata['my_color'],
                                    variant=self.game_metadata['variant'])

    def handle_iem_event(self, **kwargs) -> None:
        """Handle event from the incoming event manager"""
        # TODO: Need to ensure IEM events we are responding to in this class are specific to this game being played.
        #  Eg. We don't want to end the current game in progress, because one of our other correspondence games ended.
        if 'gameStart' in kwargs:
            event = kwargs['gameStart']['game']
            if not event['hasMoved'] and event['compat']['board']:  # TODO: There has to be a better way to ensure this is the right game...
                self._save_game_metadata(iem_gameStart=event)
                self._start_game_stream(event['gameId'])

        elif 'gameFinish' in kwargs:
            # TODO: End the streams, send data to presenter.
            # self._save_game_metadata(iem_gameFinish=event)
            pass

    def _start_game_stream(self, game_id: str) -> None:
        """Starts streaming the events of the passed in game_id"""
        self.game_stream = GameStream(game_id)
        self.game_stream.e_new_game_stream_event.add_listener(self.handle_game_stream_event)
        self.game_stream.start()

    def handle_game_stream_event(self, **kwargs) -> None:
        """Handle event from the game stream"""
        if 'gameFull' in kwargs:
            event = kwargs['gameFull']
            self._save_game_metadata(gs_gameFull=event)
            self.my_color = Color(COLOR_NAMES.index(self.game_metadata['my_color']))
            self.board_model.reinitialize_board(variant=self.game_metadata['variant'],
                                                orientation=self.my_color,
                                                fen=event['initialFen'])
            self.board_model.make_moves_from_list(event['state']['moves'].split())

        elif 'gameState' in kwargs:
            event = kwargs['gameState']
            self._save_game_metadata(gs_gameState=event)
            # moves = event['moves'].split()
            # self.board_model.make_move(moves[-1])

        elif 'chatLine' in kwargs:
            event = kwargs['chatLine']
            self._save_game_metadata(gs_chatLine=event)

        elif 'opponentGone' in kwargs:
            # TODO: Start countdown if opponent is gone. Automatically claim win if timer elapses.
            event = kwargs['opponentGone']
            self._save_game_metadata(gs_opponentGone=event)

    def _default_game_metadata(self) -> dict:
        """Returns the default structure for game metadata"""
        game_metadata = super()._default_game_metadata()
        game_metadata.update({
            'my_color': "",
            'ai_level': None,
            'rated': False,
            'speed': None,
        })
        return game_metadata

    def _save_game_metadata(self, **kwargs) -> None:
        """Parses and saves the data of the game being played.
           Raises an exception on invalid data.
        """
        try:
            if 'game_parameters' in kwargs:  # This is the data that came from the menu selections
                data = kwargs['game_parameters']
                self.game_metadata['my_color'] = data[GameOption.COLOR]
                self.game_metadata['variant'] = data[GameOption.VARIANT]
                self.game_metadata['rated'] = data.get(GameOption.RATED, False)  # Games against ai will not have this data
                self.game_metadata['ai_level'] = data.get(GameOption.COMPUTER_SKILL_LEVEL)  # Online games will not have this data
                self.game_metadata['clock']['white']['time'] = data[GameOption.TIME_CONTROL][0] * 60  # secs
                self.game_metadata['clock']['white']['increment'] = data[GameOption.TIME_CONTROL][1]  # secs
                self.game_metadata['clock']['black'] = self.game_metadata['clock']['white']

            elif 'iem_gameStart' in kwargs:
                data = kwargs['iem_gameStart']
                self.game_metadata['gameId'] = data['gameId']
                self.game_metadata['my_color'] = data['color']  # TODO: Update to use bool instead? Color(data['color')
                self.game_metadata['rated'] = data['rated']
                self.game_metadata['variant'] = data['variant']['name']
                self.game_metadata['speed'] = data['speed']

            elif 'gs_gameFull' in kwargs:
                data = kwargs['gs_gameFull']

                for color in COLOR_NAMES:
                    if data[color].get('name'):
                        self.game_metadata['players'][color]['title'] = data[color]['title']
                        self.game_metadata['players'][color]['name'] = data[color]['name']
                        self.game_metadata['players'][color]['rating'] = data[color]['rating']
                        self.game_metadata['players'][color]['provisional'] = data[color]['provisional']
                    elif data[color].get('aiLevel'):
                        self.game_metadata['players'][color]['title'] = ""
                        self.game_metadata['players'][color]['name'] = f"Stockfish level {data[color]['aiLevel']}"
                        self.game_metadata['players'][color]['rating'] = ""
                        self.game_metadata['players'][color]['provisional'] = False

                # NOTE: Times below come from lichess in milliseconds
                self.game_metadata['clock']['white']['time'] = data['state']['wtime']
                self.game_metadata['clock']['white']['increment'] = data['state']['winc']
                self.game_metadata['clock']['black']['time'] = data['state']['btime']
                self.game_metadata['clock']['black']['increment'] = data['state']['binc']

            elif 'gs_gameState' in kwargs:
                data = kwargs['gs_gameState']
                # NOTE: Times below come from lichess in milliseconds
                self.game_metadata['clock']['white']['time'] = data['wtime']
                self.game_metadata['clock']['black']['time'] = data['btime']
                self.game_metadata['status'] = data['status']

            self._notify_game_model_updated()
        except Exception as e:
            log.exception(f"Error saving online game metadata: {e}")
            raise
