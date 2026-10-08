"""wx-free mixins shared by the wx dialogs in ``dialog.py`` and ``settings/dialogs.py``.

The mixins define no ``__init__``, ``__new__``, ``__slots__`` or metaclass and go
first in the base list (``class X(Mixin, wx.Dialog)``), so they combine with the
sip classes of real wxPython and with every test stub. Nothing here imports wx:
the one wx call (the name-error message box) is the ``_show_name_error`` hook and
the one wx value (the dead-window exception type) is ``dead_window_error_types``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, TypeVar

from i18n import _
from shared.name_validation import NameValidationError

_DialogT = TypeVar("_DialogT")


class ContextManagedDialog:
    """``with Dialog(...) as dialog:`` destroys the dialog on exit and never swallows an exception."""

    def __enter__(self: _DialogT) -> _DialogT:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.Destroy()


@dataclass(frozen=True)
class NameDialogMessages:
    """Untranslated msgids (marked with ``N_`` where defined); translated when shown."""

    empty: str
    too_long: str
    invalid: str
    reserved: str | None = None
    reserved_name: str = ""

    def message_for(self, code: str) -> str:
        """The translated message for a ``NameValidationError`` code; ``reserved`` may use ``{name}``."""
        if code == "empty":
            return _(self.empty)
        if code == "too_long":
            return _(self.too_long)
        if code == "reserved" and self.reserved is not None:
            return _(self.reserved).format(name=self.reserved_name)
        return _(self.invalid)


class NameDialogBase(ContextManagedDialog):
    """``_on_ok``/``_validate_name`` of a dialog with a ``name_ctrl`` text box.

    Subclasses set ``normalize_name`` (a staticmethod) and ``name_messages`` and implement
    ``_show_name_error``.
    """

    name_messages: ClassVar[NameDialogMessages]

    @staticmethod
    def normalize_name(name: str) -> str:
        raise NotImplementedError

    def _check_name(self, candidate: str) -> tuple[str | None, str | None]:
        try:
            return self.normalize_name(candidate), None
        except NameValidationError as error:
            code = error.code
        except ValueError:
            code = "invalid"
        return None, self.name_messages.message_for(code)

    def _validate_name(self, candidate: str) -> str | None:
        return self._check_name(candidate)[1]

    def _on_ok(self, event) -> None:
        normalized, message = self._check_name(self.name_ctrl.GetValue())
        if message:
            self._show_name_error(message)
            self.name_ctrl.SetFocus()
            return
        self.name_ctrl.SetValue(normalized)
        event.Skip()

    def _show_name_error(self, message: str) -> None:
        raise NotImplementedError


class SingletonDialogMixin:
    """At most one open dialog per class; ``show_singleton`` raises it or builds a new one.

    The open dialog lives in the class's own ``_instance`` (read through ``cls.__dict__``,
    so a subclass never sees its parent's dialog).
    """

    dead_window_error_types: ClassVar[tuple[type[BaseException], ...]] = ()

    @classmethod
    def _raise_existing(cls, prepare=None):
        """Raise and return the open dialog; ``None`` when there is none or it was destroyed."""
        instance = cls.__dict__.get("_instance")
        if instance is None:
            return None
        try:
            instance.Iconize(False)
            if prepare is not None:
                prepare(instance)
            instance.Raise()
            instance.SetFocus()
            return instance
        except (ReferenceError, RuntimeError, *cls.dead_window_error_types) as error:
            if not cls._is_destroyed_window_error(error):
                raise
            cls._instance = None
            return None

    @classmethod
    def _show_new(cls, instance):
        cls._instance = instance
        instance.Show()
        return instance

    @classmethod
    def open_instance(cls):
        """The open dialog of this class, or ``None``. Nothing is raised, focused or checked."""
        return cls.__dict__.get("_instance")

    def _destroy(self) -> None:
        owner = type(self)
        if owner.__dict__.get("_instance") is self:
            owner._instance = None
        self.Destroy()

    @classmethod
    def _is_destroyed_window_error(cls, error: BaseException) -> bool:
        if isinstance(error, cls.dead_window_error_types):
            return True
        if not isinstance(error, (ReferenceError, RuntimeError)):
            return False
        message = str(error).lower()
        return (
            "wrapped c/c++ object" in message
            or "has been deleted" in message
            or "already deleted" in message
            or "destroyed" in message
        )
