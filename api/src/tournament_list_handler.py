import webapp2
import json

from generic_handler import GenericHandler
from google.appengine.api import users
from google.appengine.ext import ndb
from handler_utils import BuildMovementAndMaybeSetStatus
from handler_utils import CheckUserLoggedInAndMaybeReturnStatus
from handler_utils import is_int
from handler_utils import SetErrorStatus
from models import Tournament
from models import PlayerPair
from python import boardgenerator

class TourneyListHandler(GenericHandler):
  def get(self):
    user = users.get_current_user()
    if not CheckUserLoggedInAndMaybeReturnStatus(self.response, user):
      return

    # TODO: Implement paging if ever needed.
    tourneys = Tournament._query(Tournament.owner_id == 
        user.user_id()).fetch(projection=[Tournament.name])
    tourney_list =  [{"id": str(t.key.id()), "name": t.name} for t in tourneys]
    self.response.set_status(200)
    self.response.headers['Content-Type'] = 'application/json'
    self.response.out.write(json.dumps({"tournaments": tourney_list}, indent=2))


  def post(self):
    user = users.get_current_user()
    if not CheckUserLoggedInAndMaybeReturnStatus(self.response, user):
      return

    request_dict = self._ParseRequestInfoAndMaybeSetStatus()
    if not request_dict:
      return

    name = request_dict['name']
    no_pairs = request_dict['no_pairs']
    no_boards = request_dict['no_boards']
    player_list = request_dict.get('players')
    if not self._CheckValidTournamentInfoAndMaybeSetStatus(name, no_pairs,
                                                           no_boards,
                                                           player_list):
      return

    tourney = Tournament.CreateAndPersist(owner_id=user.user_id(),
                                          name = name,
                                          no_pairs=no_pairs,
                                          no_boards=no_boards,
                                          boards=boardgenerator.GenerateBoards(35))
    tourney.PutPlayers(player_list, no_pairs)
    self.response.set_status(201)
    self.response.headers['Content-Type'] = 'application/json'
    self.response.out.write(json.dumps({"id": str(tourney.key.id())}))


  def _ParseRequestInfoAndMaybeSetStatus(self):
    ''' Parses the body of the request. Checks if the body is valid JSON with
        all the proper fields set. Checks if the number of boards and number of 
        pairs are valid numbers. If not sets the response with the appropriate
        status and error message.
    '''
    try:
      request_dict = json.loads(self.request.body)
    except ValueError:
      SetErrorStatus(self.response, 500, "Invalid Input",
                     "Unable to parse request body as JSON object")
      return None
    if not isinstance(request_dict.get('no_pairs'), int):
      SetErrorStatus(self.response, 400, "Invalid Input",
                     "no_pairs must be an integer")
      return None
    elif not isinstance(request_dict.get('no_boards'), int):
      SetErrorStatus(self.response, 400, "Invalid Input",
                     "no_boards must be an integer")
      return None
    elif request_dict.get('players'):
      player_list = request_dict.get('players')
      for player in player_list:
        if not player['pair_no']:
          SetErrorStatus(self.response, 400, "Invalid Input",
                         "Player must have corresponding pair number if present.")
          return None
        if not isinstance(player['pair_no'], int):
          SetErrorStatus(self.response, 400, "Invalid Input",
                         "Player pair number must be an integer, was {}".format(
                             player['pair_no']))
          return None
    return request_dict


  def _CheckValidTournamentInfoAndMaybeSetStatus(self, name, no_pairs,
                                                 no_boards, players=None):
    ''' Checks if the input is valid and sane. 
        If not sets the response with the appropriate status and error message.
        Assumes no_pairs and no_boards are integers.
    '''
    if name == "":
      SetErrorStatus(self.response, 400, "Invalid input",
                     "Tournament name must be nonempty")
      return False
    elif no_pairs < 2:
      SetErrorStatus(self.response, 400, "Invalid input",
                     "Number of pairs must be > 1, was {}".format(no_pairs))
      return False
    elif no_boards < 1:
      SetErrorStatus(self.response, 400, "Invalid input",
                     "Number of boards must be > 0, was {}".format(no_boards))
      return False
    elif players:
      for player in players:
        if player['pair_no'] < 1 or player['pair_no'] > no_pairs:
          SetErrorStatus(self.response, 400, "Invalid Input",
                         "Player pair must be between 1 and no_pairs, was {}.".format(
                             player['pair_no']))
          return False
    return BuildMovementAndMaybeSetStatus(
        self.response, no_pairs, no_boards) is not None
