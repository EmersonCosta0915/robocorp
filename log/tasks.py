import os
import subprocess
import sys
from pathlib import Path

from invoke import task

ROOT = Path(__file__).absolute().parent

try:
    import devutils
except ImportError:
    devutils_src = ROOT.parent / "devutils" / "src"
    assert devutils_src.exists(), f"{devutils_src} does not exist!"
    sys.path.append(str(devutils_src))

from devutils.invoke_utils import build_common_tasks

common_tasks = build_common_tasks(
    ROOT,
    "robocorp.log",
    ruff_format_arguments=(
        r"--exclude=_index.py --exclude=_index_v2.py --exclude=_index_v3.py"
    ),
)
globals().update(common_tasks)


@task
def build_output_view_react(ctx, dev=False):
    """
    Builds the react-based output view in prod mode in `dist`.
    """
    import shutil

    src_webview_react = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "output-react",
        )
    )

    # Note: this is now called from the ci configuration directly because
    # the environment being passed in the ci was not being properly used
    # (didn't discover why that was the case).
    #
    # This means that `npm install` or `npm ci` must be manually
    # called before `inv build-output-view-react`.
    #
    # try:
    #     subprocess.check_call(["npm", "ci"], cwd=src_webview_react, shell=shell)
    # except:
    #     import traceback
    #
    #     traceback.print_exc()
    #     raise RuntimeError(
    #         f"HAS_CI: {'CI' in os.environ} HAS_NODE_AUTH_TOKEN: {'NODE_AUTH_TOKEN' in os.environ}"
    #     )

    print("=== npm run build")
    shell = sys.platform == "win32"
    vtag = "_v3"
    subprocess.check_call(
        ["npm", "run"] + (["build:debug"] if dev else ["build"]),
        cwd=src_webview_react,
        shell=shell,
    )

    index_in_dist = os.path.join(src_webview_react, f"dist{vtag}", "index.html")
    assert os.path.exists(index_in_dist)

    robocorp_code_folder = (
        Path(index_in_dist).parent.parent.parent.parent.parent
        / "robotframework-lsp"
        / "robocorp-code"
    )
    if robocorp_code_folder.exists():
        # i.e.: The language server sources are checked out right next
        # to the robo sources. Copy the contents to the output.html expected
        # by Robocorp Code.
        target = robocorp_code_folder / "vscode-client" / "templates" / "output.html"
        print(f"Copying output-react to: {target}")
        shutil.copyfile(index_in_dist, str(target))

        # Note: to have it automatically built, it's possible to go to the folder:
        # /robo/log
        # and then (with "pip install watchfiles") run:
        # watchfiles "inv build-output-view-react --dev" ./output-react/src

    # Now, let's embed the contents of the index.html into a python
    # module where it can be saved accordingly.

    index_in_src = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "src",
            "robocorp",
            "log",
            f"_index{vtag}.py",
        )
    )

    file_contents = {}

    dist_dirname = os.path.dirname(index_in_dist)
    for filename in os.listdir(dist_dirname):
        with open(os.path.join(dist_dirname, filename), encoding="utf-8") as stream:
            file_contents[filename] = stream.read()

    assert "index.html" in file_contents

    with open(index_in_src, "w", encoding="utf-8") as stream:
        stream.write(
            f"""# coding: utf-8
# Note: autogenerated file.
# To regenerate this file use: inv build-output-view-react.

# The FILE_CONTENTS contains the contents of the files with
# html/javascript code which can be used to visualize the contents of the
# output generated by robocorp-log (i.e.: the .log files).

FILE_CONTENTS = {repr(file_contents)}
"""
        )
