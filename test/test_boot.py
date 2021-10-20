#
# This file is part of LiteX.
#
# Copyright (c) 2021 Navaneeth Bhardwaj <navan93@gmail.com>
# SPDX-License-Identifier: BSD-2-Clause

import subprocess
import unittest

class TestCPU(unittest.TestCase):
    def test_boot(self):
        cmd = 'lxsim --bios-test-mode --sim-debug --non-interactive'
        cmd = cmd.split(' ')
        result = subprocess.check_output(cmd)
        result = str(result)
        print(result)
        if 'Bios successfully booted.' not in result:
            self.fail()

