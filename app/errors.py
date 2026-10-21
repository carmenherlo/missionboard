"""Errors raised by services when a rule is broken.

Services know nothing about HTTP; main.py maps each error to a status code.
"""


class DomainError(Exception):
    pass


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class InvalidError(DomainError):
    pass


class PermissionDeniedError(DomainError):
    pass


class TooLargeError(DomainError):
    pass


class UnsupportedTypeError(DomainError):
    pass
