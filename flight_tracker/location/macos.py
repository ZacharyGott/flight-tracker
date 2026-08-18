"""macOS Core Location adapter."""

from collections.abc import Callable
from importlib import import_module
from threading import Timer
from typing import Any, Protocol, cast

from ..geo import Position
from .exceptions import (
    LocationError,
    LocationPermissionError,
    LocationTimeoutError,
    LocationUnavailableError,
)


class NativeCoordinate(Protocol):
    """The coordinate values exposed by a Core Location object."""

    latitude: float
    longitude: float


class NativeLocation(Protocol):
    """The part of a Core Location value used by this adapter."""

    def coordinate(self) -> NativeCoordinate:
        """Return the location coordinate."""
        ...


def position_from_native_location(location: NativeLocation) -> Position:
    """Convert a Core Location value to the shared position type."""
    coordinate = location.coordinate()
    return Position(float(coordinate.latitude), float(coordinate.longitude))


class _LocationSession(Protocol):
    def get_position(self, timeout_seconds: float) -> Position:
        """Return one position from the native location service."""
        ...


class MacOSLocationProvider:
    """Read one position from macOS Core Location."""

    def __init__(
        self,
        timeout_seconds: float = 10.0,
        session_factory: Callable[[], _LocationSession] | None = None,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._session_factory = session_factory or _PyObjCLocationSession

    def get_position(self) -> Position:
        """Return one position from macOS location services."""
        return self._session_factory().get_position(self._timeout_seconds)


class _PyObjCLocationSession:
    """Run one Core Location request through the macOS event loop."""

    def __init__(self) -> None:
        try:
            self._core_location: Any = import_module("CoreLocation")
            self._foundation: Any = import_module("Foundation")
            self._objc: Any = import_module("objc")
            self._app_helper: Any = import_module("PyObjCTools.AppHelper")
        except ImportError as error:
            raise LocationUnavailableError(
                "macOS Core Location dependencies are not installed"
            ) from error

        self._result: Position | None = None
        self._error: LocationError | None = None
        self._manager: Any = self._core_location.CLLocationManager.alloc().init()
        self._delegate = self._create_delegate()
        self._manager.setDelegate_(self._delegate)

    def get_position(self, timeout_seconds: float) -> Position:
        """Request one position and wait for the native callback."""
        if not self._manager.locationServicesEnabled():
            raise LocationUnavailableError("macOS location services are disabled")

        status = self._manager.authorizationStatus()
        if status == self._core_location.kCLAuthorizationStatusDenied:
            raise LocationPermissionError("macOS location permission was denied")
        if status == self._core_location.kCLAuthorizationStatusRestricted:
            raise LocationPermissionError("macOS location permission is restricted")

        timer = Timer(timeout_seconds, self._finish_with_timeout)
        timer.start()
        try:
            if status == self._core_location.kCLAuthorizationStatusNotDetermined:
                self._manager.requestWhenInUseAuthorization()
            else:
                self._manager.startUpdatingLocation()
            self._app_helper.runConsoleEventLoop()
        finally:
            timer.cancel()
            self._manager.stopUpdatingLocation()

        if self._error is not None:
            raise self._error
        if self._result is None:
            raise LocationUnavailableError("macOS returned no location")
        return self._result

    def _create_delegate(self) -> Any:
        owner = self
        foundation = self._foundation
        objc = self._objc

        class Delegate(foundation.NSObject):
            def locationManager_didUpdateLocations_(
                self,
                manager: Any,
                locations: Any,
            ) -> None:
                del manager
                if not locations:
                    return
                owner._finish_with_location(cast(NativeLocation, locations[-1]))

            def locationManager_didFailWithError_(
                self,
                manager: Any,
                error: Any,
            ) -> None:
                del manager, error
                owner._finish_with_error(
                    LocationUnavailableError("macOS location provider failed")
                )

            def locationManagerDidChangeAuthorization_(self, manager: Any) -> None:
                status = manager.authorizationStatus()
                if status == owner._core_location.kCLAuthorizationStatusDenied:
                    owner._finish_with_error(
                        LocationPermissionError("macOS location permission was denied")
                    )
                elif status == owner._core_location.kCLAuthorizationStatusRestricted:
                    owner._finish_with_error(
                        LocationPermissionError("macOS location permission is restricted")
                    )
                elif status != owner._core_location.kCLAuthorizationStatusNotDetermined:
                    manager.startUpdatingLocation()

            def init(self) -> Any:
                return objc.super(Delegate, self).init()

        return Delegate.alloc().init()

    def _finish_with_location(self, location: NativeLocation) -> None:
        try:
            self._result = position_from_native_location(location)
        except ValueError:
            self._finish_with_error(
                LocationUnavailableError("macOS returned invalid coordinates")
            )
            return
        self._stop_event_loop()

    def _finish_with_error(self, error: LocationError) -> None:
        self._error = error
        self._stop_event_loop()

    def _finish_with_timeout(self) -> None:
        self._finish_with_error(
            LocationTimeoutError("macOS did not return a location before the timeout")
        )

    def _stop_event_loop(self) -> None:
        self._app_helper.stopEventLoop()
