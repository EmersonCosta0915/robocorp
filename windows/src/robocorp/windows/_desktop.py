import time
import typing
from typing import Iterator, List, Optional

from robocorp.windows._control_element import ControlElement
from robocorp.windows.protocols import Locator

if typing.TYPE_CHECKING:
    from robocorp.windows._iter_tree import ControlTreeNode
    from robocorp.windows._window_element import WindowElement
    from robocorp.windows.vendored.uiautomation.uiautomation import Control


class Desktop(ControlElement):
    """
    The desktop is the control, containing other top-level windows.

    The elements provided by robocorp-windows are organized as:
        Desktop (root control)
            WindowElement (top-level windows)
                ControlElement (controls inside a window)
    """

    def __init__(self):
        from robocorp.windows._config_uiautomation import _config_uiautomation
        from robocorp.windows._find_ui_automation import find_ui_automation_wrapper

        _config_uiautomation()

        ControlElement.__init__(self, find_ui_automation_wrapper("desktop"))

    # Overridden just to change the default max_depth to 1
    def print_tree(
        self, stream=None, show_properties: bool = False, max_depth: int = 1
    ) -> None:
        """
        Print a tree of control elements.

        A Windows application structure can contain multilevel element structure.
        Understanding this structure is crucial for creating locators. (based on
        controls' details and their parent-child relationship)

        This keyword can be used to output logs of application's element structure.

        The printed element attributes correspond to the values that may be used
        to create a locator to find the actual wanted element.

        Args:
            stream: The stream to which the text should be printed (if not given,
                sys.stdout is used).

            show_properties: Whether the properties of each element should
                be printed (off by default as it can be considerably slower
                and makes the output very verbose).

            max_depth: Up to which depth the tree should be printed.

        Example:

            Print the top-level window elements:

            ```python
            from robocorp import windows
            windows.desktop().print_tree()
            ```

        Example:

            Print the tree starting at some other element:

            ```python
            from robocorp import windows
            windows.find_window("Calculator").find("path:2|3").print_tree()
            ```
        """

        return ControlElement.print_tree(
            self, stream=stream, show_properties=show_properties, max_depth=max_depth
        )

    def _iter_children_nodes(
        self, *, max_depth: int = 1
    ) -> Iterator["ControlTreeNode[ControlElement]"]:
        """
        Internal API to provide structure with a `ControlTreeNode` for printing.
        Not part of the public API (should not be used by client code).
        """
        return ControlElement._iter_children_nodes(self, max_depth=max_depth)

    def iter_children(self, *, max_depth: int = 1) -> Iterator["ControlElement"]:
        """
        Iterates over all of the children of this element up to the max_depth
        provided.

        Args:
            max_depth: the maximum depth which should be iterated to.

        Returns:
            An iterator of `ControlElement` which provides the descendants of
            this element.

        Note:
            Iteration over too many items can be slow. Try to keep the
            max depth up to a minimum to avoid slow iterations.
        """
        return ControlElement.iter_children(self, max_depth=max_depth)

    def find_window(
        self,
        locator: Locator,
        search_depth: int = 1,
        timeout: Optional[float] = None,
        wait_time: Optional[float] = None,
        foreground: bool = True,
    ) -> "WindowElement":
        """
        Finds windows matching the given locator.

        Args:
            locator: The locator which should be used to find a window.

            search_depth: The search depth to be used to find the window (by default
                equals 1, meaning that only top-level windows will be found).

            timeout:
                The search for a child with the given locator will be retried
                until the given timeout elapses.

                At least one full search up to the given depth will always be done
                and the timeout will only take place afterwards.

                If not given the global config timeout will be used.

            wait_time:
                The time to wait after the windows was found.

                If not given the global config wait_time will be used.

            foreground:
                If True the matched window will be made the foreground window.

        Raises:
            ElementNotFound if a window with the given locator could not be
            found.
        """
        from robocorp.windows import _find_window

        return _find_window.find_window(
            None, locator, search_depth, timeout, wait_time, foreground
        )

    def find_windows(
        self,
        locator: Locator,
        search_depth: int = 1,
        timeout: Optional[float] = None,
        wait_for_window: bool = False,
    ) -> List["WindowElement"]:
        """
        Finds windows matching the given locator.

        Args:
            locator: The locator which should be used to find windows (if not
                given, all windows are returned).

            search_depth: The search depth to be used to find windows (by default
                equals 1, meaning that only top-level windows will be found).

            timeout:
                The search for a child with the given locator will be retried
                until the given timeout elapses.

                At least one full search up to the given depth will always be done
                and the timeout will only take place afterwards.

                If not given the global config timeout will be used.

                Only used if `wait_for_window` is True.

            wait_for_window: Defines whether the search should keep on searching
                until a window with the given locator is found (note that if True
                and no window was found a ElementNotFound is raised).

        Returns:
            The `WindowElement`s which should be used to interact with the window.

        Example:

            ```python
            window = find_windows('Calculator')
            window = find_windows('name:Calculator')
            window = find_windows('subname:Notepad')
            window = find_windows('regex:.*Notepad')
            window = find_windows('executable:Spotify.exe')
            ```
        """
        from robocorp.windows import _find_window

        return _find_window.find_windows(
            None, locator, search_depth, timeout, wait_for_window, search_strategy="all"
        )

    def close_windows(
        self,
        locator: Locator,
        search_depth: int = 1,
        timeout: Optional[float] = None,
        wait_for_window: bool = False,
        wait_time: Optional[float] = 0,
    ) -> int:
        """
        Closes the windows matching the given locator. Note that internally
        this will force-kill the processes with the related `pid` as well
        as all of the child processes of that `pid`.

        Args:
            locator: The locator which should be used to find windows to be closed.

            search_depth: The search depth to be used to find windows (by default
                equals 1, meaning that only top-level windows will be closed).
                Note that windows are closed by force-killing the pid related
                to the window.

            timeout:
                The search for a window with the given locator will be retried
                until the given timeout elapses. At least one full search up to
                the given depth will always be done and the timeout will only
                take place afterwards (if `wait_for_window` is True).

                Only used if `wait_for_window` is True.

                If not given the global config timeout will be used.

            wait_for_window: If True windows this method will keep searching for
                windows until a window is found or until the timeout is reached
                (an ElementNotFound is raised if no window was found until the
                timeout is reached, otherwise an empty list is returned).

            wait_time: A time to wait after closing each window.

        Returns:
            The number of closed windows.

        Raises:
            ElementNotFound: if wait_for_window is True and the timeout was reached.
        """

        from robocorp.windows import config

        windows_elements = self.find_windows(
            locator, search_depth, timeout=timeout, wait_for_window=wait_for_window
        )

        if wait_time is None:
            wait_time = config().wait_time

        closed = 0
        for element in windows_elements:
            if element.close_window():
                closed += 1
                if wait_time:
                    time.sleep(wait_time)
        return closed

    def windows_run(self, text: str, wait_time: float = 1) -> None:
        """
        Use Windows `Run window` to launch an application.

        Activated by pressing `Win + R`. Then the app name is typed in and finally the
        "Enter" key is pressed.

        Args:
            text: Text to enter into the Run input field. (e.g. `Notepad`)
            wait_time: Time to sleep after the searched app is executed. (1s by
                default)
        """

        # NOTE(cmin764): The waiting time after each key set sending can be controlled
        #  globally and individually with the config wait_time.
        self.send_keys(keys="{Win}r")
        self.send_keys(keys=text, interval=0.01)
        self.send_keys(send_enter=True)
        time.sleep(wait_time)

    def windows_search(self, text: str, wait_time: float = 3.0) -> None:
        """
        Use Windows `search window` to launch application.

        Activated by pressing `win + s`.

        Args:
            text: Text to enter into search input field (e.g. `Notepad`)
            wait_time: sleep time after search has been entered (default 3.0 seconds)
        """
        search_cmd = "{Win}s"
        if self.get_win_version() == "11":
            search_cmd = search_cmd.rstrip("s")
        self.send_keys(search_cmd)
        self.send_keys(text)
        self.send_keys("{Enter}")
        time.sleep(wait_time)

    def get_win_version(self) -> str:
        """
        Windows only utility which returns the current Windows major version.
        """
        # Windows terminal `ver` command is bugged, until that's fixed, check by build
        #  number. (the same applies for `platform.version()`)
        import platform

        version_parts = platform.version().split(".")
        major = version_parts[0]
        if major == "10" and int(version_parts[2]) >= 22000:
            major = "11"

        return major

    def wait_for_active_window(
        self, locator: Locator, timeout: Optional[float] = None
    ) -> "WindowElement":
        """
        Waits for a window with the given locator to be made active.

        Args:
            locator: The locator that the active window must match.
            timeout: Timeout to wait for a window with the given locator to be
                made active.

        Raises:
            ElementNotFound if no window was found as active until the timeout
            was reached.

        Note: if there's a matching window which matches the locator but it's not
            the active one, this will fail (consider using `find_window`
            for this use case).
        """
        from robocorp.windows import config
        from robocorp.windows._errors import ElementNotFound
        from robocorp.windows._find_ui_automation import _matches
        from robocorp.windows._find_window import _iter_window_locators
        from robocorp.windows._iter_tree import ControlTreeNode
        from robocorp.windows._match_object import MatchObject
        from robocorp.windows._ui_automation_wrapper import (
            _UIAutomationControlWrapper,
            empty_location_info,
        )
        from robocorp.windows._window_element import WindowElement
        from robocorp.windows.vendored.uiautomation.uiautomation import (
            GetForegroundControl,
        )

        locator_parts = locator.split(MatchObject.TREE_SEP)
        if not locator_parts:
            raise AssertionError(f"The locator passed ({locator!r}) is not valid.")
        if len(locator_parts) > 1:
            raise AssertionError(
                f"The locator passed ({locator!r}) can only have one "
                "level in this API ('>' not allowed)."
            )

        if timeout is None:
            timeout = config().timeout

        check_search_params = []
        for loc in _iter_window_locators(locator):
            search_params = MatchObject.parse_locator(loc).as_search_params()
            if "depth" in search_params:
                raise AssertionError('"depth" locator not valid for this API.')
            if "path" in search_params:
                raise AssertionError('"path" locator not valid for this API.')
            if "desktop" in search_params:
                raise AssertionError('"desktop" locator not valid for this API.')
            check_search_params.append(search_params)

        timeout_at = time.monotonic() + timeout
        while True:
            control = GetForegroundControl()

            while control is not None:
                if control.GetParentControl() is None:
                    # We don't want to check the desktop itself
                    break

                for search_params in check_search_params:
                    tree_node: "ControlTreeNode[Control]" = ControlTreeNode(
                        control, 0, 0, ""
                    )
                    if _matches(search_params, tree_node):
                        el = WindowElement(
                            _UIAutomationControlWrapper(control, empty_location_info())
                        )
                        return el

                control = control.GetParentControl()

            if time.monotonic() > timeout_at:
                # Check only after at least one search was done.
                msg = (
                    "No active window was found as active with the locator: "
                    f"{locator!r}."
                )

                if control is not None:
                    el = WindowElement(
                        _UIAutomationControlWrapper(control, empty_location_info())
                    )
                    msg += f"\nActive window: {el}"
                else:
                    msg += "\nNo active window found."

                curr_windows = self.find_windows("regex:.*")
                if curr_windows:
                    msg += "\nExisting Windows:\n"
                    for w in curr_windows:
                        msg += f"{w}\n"

                self.log_screenshot()
                raise ElementNotFound(msg)
            else:
                time.sleep(1 / 15.0)

    def drag_and_drop(
        self,
        source_element: Locator,
        target_element: Locator,
        speed: float = 1.0,
        copy: Optional[bool] = False,
        wait_time: float = 1.0,
        timeout: Optional[float] = None,
    ):
        """Drag and drop the source element into target element.

        :param source: source element for the operation
        :param target: target element for the operation
        :param speed: adjust speed of operation, bigger value means more speed
        :param copy: on True does copy drag and drop, defaults to move
        :param wait_time: time to wait after drop, default 1.0 seconds

        Example:

        .. code-block:: robotframework

            # copying a file, report.html, from source (File Explorer) window
            # into a target (File Explorer) Window
            # locator
            Drag And Drop
            ...    name:C:\\temp type:Windows > name:report.html type:ListItem
            ...    name:%{USERPROFILE}\\Documents\\artifacts type:Windows > name:"Items View"
            ...    copy=True

        Example:

        .. code-block:: robotframework

            # moving *.txt files into subfolder within one (File Explorer) window
            ${source_dir}=    Set Variable    %{USERPROFILE}\\Documents\\test
            Control Window    name:${source_dir}
            ${files}=    Find Files    ${source_dir}${/}*.txt
            # first copy files to folder2
            FOR    ${file}    IN    @{files}
                Drag And Drop    name:${file.name}    name:folder2 type:ListItem    copy=True
            END
            # second move files to folder1
            FOR    ${file}    IN    @{files}
                Drag And Drop    name:${file.name}    name:folder1 type:ListItem
            END
        """  # noqa: E501
        import robocorp.windows.vendored.uiautomation as auto
        from robocorp.windows import config

        source = self.find(source_element, timeout=timeout)
        target = self.find(target_element, timeout=timeout)
        try:
            if copy:
                auto.PressKey(auto.Keys.VK_CONTROL)
            auto.DragDrop(
                source.xcenter,
                source.ycenter,
                target.xcenter,
                target.ycenter,
                moveSpeed=speed,
                waitTime=wait_time,
            )
        finally:
            if copy:
                click_wait_time: float = (
                    wait_time if wait_time is not None else config().wait_time
                )
                self._click_element(source, "Click", click_wait_time)
                auto.ReleaseKey(auto.Keys.VK_CONTROL)
