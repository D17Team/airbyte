#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#


import sys

from airbyte_cdk.entrypoint import launch
from source_connatix import SourceConnatix

if __name__ == "__main__":
    source = SourceConnatix()
    launch(source, sys.argv[1:])
