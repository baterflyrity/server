import gc
from unittest import mock

import pytest
from trueskill import Rating

from server.factions import Faction
from server.players import Player
from server.protocol import DisconnectedError
from server.rating import Leaderboard, RatingType


@pytest.fixture
def leaderboards():
    global_ = Leaderboard(1, "global")
    return {
        "global": global_,
        "ladder_1v1": Leaderboard(2, "ladder_1v1"),
        "tmm_2v2": Leaderboard(3, "tmm_2v2", global_)
    }


def test_ratings(leaderboards):
    p = Player("Schroedinger", leaderboards=leaderboards)
    p.ratings[RatingType.GLOBAL] = (1500, 20)
    assert p.ratings[RatingType.GLOBAL] == (1500, 20)
    p.ratings[RatingType.GLOBAL] = Rating(1700, 20)
    assert p.ratings[RatingType.GLOBAL] == (1700, 20)
    assert p.ratings["tmm_2v2"] == (1700, 170)
    p.ratings[RatingType.LADDER_1V1] = (1200, 20)
    assert p.ratings[RatingType.LADDER_1V1] == (1200, 20)
    p.ratings[RatingType.LADDER_1V1] = Rating(1200, 20)
    assert p.ratings[RatingType.LADDER_1V1] == (1200, 20)
    assert p.ratings["Something completely different"] == (1500, 500)


def test_faction():
    """
    Yes, this test was motivated by a bug
    """
    p = Player("Schroedinger2")
    p.faction = "aeon"
    assert p.faction == Faction.aeon
    p.faction = Faction.aeon
    assert p.faction == Faction.aeon


def test_object_equality():
    p1 = Player("Arthur", 42)
    p2 = Player("Arthur", 42)
    assert p1 == p1
    assert p1 != p2
    assert hash(p1) == hash(p1)


def test_weak_references():
    p = Player("Test")
    weak_properties = ["lobby_connection", "game", "game_connection"]
    referent = mock.Mock()
    for prop in weak_properties:
        setattr(p, prop, referent)

    del referent
    gc.collect()

    for prop in weak_properties:
        assert getattr(p, prop) is None


def test_unlink_weakref():
    p = Player("Test")
    mock_game = mock.Mock()
    p.game = mock_game
    assert p.game == mock_game
    del p.game
    assert p.game is None


def test_serialize():
    p = Player(
        player_id=42,
        login="Something",
        ratings={
            RatingType.GLOBAL: (1234, 68),
            RatingType.LADDER_1V1: (1500, 230),
        },
        clan="TOAST",
        game_count={RatingType.GLOBAL: 542}
    )
    assert p.to_dict() == {
        "id": 42,
        "login": "Something",
        "clan": "TOAST",
        "state": "offline",
        "ratings": {
            "global": {
                "rating": (1234, 68),
                "number_of_games": 542
            },
            "ladder_1v1": {
                "rating": (1500, 230),
                "number_of_games": 0
            }
        },
    }


def test_serialize_state():
    conn = mock.Mock()
    p = Player(lobby_connection=conn)
    assert "state" not in p.to_dict()

    del p.lobby_connection
    assert p.to_dict()["state"] == "offline"


async def test_send_message():
    p = Player("Test")

    assert p.lobby_connection is None
    with pytest.raises(DisconnectedError):
        await p.send_message({})


def test_write_message():
    p = Player("Test")

    assert p.lobby_connection is None
    # Should not raise
    p.write_message({})


def test_write_message_while_disconnecting(player_factory):
    p = player_factory("Test", lobby_connection_spec="auto")
    p.lobby_connection.write.side_effect = DisconnectedError()

    # Should not raise
    p.write_message({})
