"""Utility functions for SCM Tiles."""
# Copyright 2016 Andrew Dawson
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time


def get_logger(log_file):
    """
    Return a logging function that logs to a particular file or
    file-like object.

    **Argument:**

    * log_file
        A file or file-like object to define the logger on.

    **Returns:**

    * logger
        A callable accepting a single input, which consists of a message
        (anything that can be converted to a string) which will be
        logged to the file defined by `log_file` with the date and time
        prepended to the message.

    """
    def _log(message):
        line = '[{}] {!s}\n'.format(time.strftime('%F %T'), message)
        log_file.write(line)
    return _log
