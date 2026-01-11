from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings


@dataclass(frozen=True)
class GameConfig:
    key: str
    oracle_name: str
    game_name_en: str
    game_name_zh: str
    main_count: int
    max_number: int
    theme_class: str
    data_sources: dict

    @property
    def small_threshold(self) -> int:
        return max(1, self.max_number // 2)


def get_game_config(game_key: str | None) -> GameConfig:
    games = settings.LOTTO_GAMES
    default_key = getattr(settings, 'LOTTO_DEFAULT_GAME', next(iter(games)))
    key = game_key if game_key in games else default_key
    config = games[key]
    return GameConfig(
        key=key,
        oracle_name=config.get('oracle_name', key),
        game_name_en=config.get('game_name_en', config.get('game_name', key)),
        game_name_zh=config.get('game_name_zh', config.get('game_name', key)),
        main_count=int(config.get('main_count', 7)),
        max_number=int(config.get('max_number', 50)),
        theme_class=config.get('theme_class', ''),
        data_sources=config.get('data_sources', {}),
    )


def get_supported_games() -> list[GameConfig]:
    return [get_game_config(key) for key in settings.LOTTO_GAMES.keys()]
