from __future__ import annotations
from typing import TYPE_CHECKING

from collections import deque

from trueseeing.core.model.cmd import CommandMixin
from trueseeing.core.ui import ui

if TYPE_CHECKING:
  from typing import Dict, Any
  from trueseeing.api import CommandHelper, Command, CommandMap, ConfigEntry, ModifierMap, ModifierEvent

class ConfigCommand(CommandMixin):
  _confbag: Dict[str, ConfigEntry]
  _stash: Dict[str, Any]

  def __init__(self, helper: CommandHelper) -> None:
    self._helper = helper
    self._confbag = self._helper._confbag  # type:ignore[attr-defined]
    self._stash = dict()

  @staticmethod
  def create(helper: CommandHelper) -> Command:
    return ConfigCommand(helper)

  def get_commands(self) -> CommandMap:
    return {
      '?e?':dict(e=self._help, n='?e?', d='config help'),
      'e':dict(e=self._manip, n='e key[=value]', d='get/set config'),
    }

  def get_modifiers(self) -> ModifierMap:
    return {
      'e':dict(e=self._mod, n='@e:key=value', d='bind the config for the command'),
    }

  async def _help(self, args: deque[str]) -> None:
    ui.success('Configs:')
    if self._confbag:
      width = (2 + max([len(e.get('d', '')) for e in self._confbag.values()]) // 4) * 4
      for k in sorted(self._confbag):
        e = self._confbag[k]
        if 'n' in e:
          ui.stderr(
            f'{{n:<{width}s}}{{d}}'.format(n=e['n'], d=e['d'])
          )

  async def _manip(self, args: deque[str]) -> None:
    from trueseeing.core.exc import InvalidConfigKeyError
    _ = args.popleft()
    if not args:
      ui.fatal('need a config key')
    kv = args.popleft()
    if args:
      ui.fatal('got an unexpected token (try e key=value to set)')
    try:
      if '=' not in kv:
        key = kv
        ui.info('{}: {}'.format(key, self._helper.get_config(key)))
      else:
        key, value = kv.split('=')
        if not value:
          ui.fatal('need a value')
        self._helper.set_config(key, value)
    except InvalidConfigKeyError:
      ui.fatal(f'unknown key: {key}')

  async def _mod(self, ev: ModifierEvent, val: str) -> None:
    from trueseeing.core.exc import InvalidConfigKeyError
    if '=' not in val:
      ui.fatal('need a value')
    try:
      k, v = val.split('=')
      if ev == 'begin':
        if k in self._stash:
          ui.fatal(f'config key is already bound: {k}')
        ov = self._helper.get_config(k)
        self._helper.set_config(k, v)
        self._stash[k] = ov
      elif ev == 'end':
        assert k in self._stash
        try:
          self._helper.set_config(k, self._stash[k])
        finally:
          del self._stash[k]
    except InvalidConfigKeyError:
      ui.fatal(f'unknown key: {k}')
