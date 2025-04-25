#!/usr/bin/env python3
#  coding=utf-8
#  vim:ts=4:sts=4:sw=4:et
#
#  Author: Hari Sekhon
#  Date: 2025-04-26 00:37:28 +0800 (Sat, 26 Apr 2025)
#
#  https///github.com/HariSekhon/DevOps-Python-tools
#
#  License: see accompanying Hari Sekhon LICENSE file
#
#  If you're using my code you're welcome to connect with me on LinkedIn
#  and optionally send me feedback to help steer this or other code I publish
#
#  https://www.linkedin.com/in/HariSekhon
#

"""

Plots the Marriage rates in England & Wales using the latest download from the UK Government website:

    https://www.ons.gov.uk/peoplepopulationandcommunity/birthsdeathsandmarriages/marriagecohabitationandcivilpartnerships/bulletins/marriagesinenglandandwalesprovisional/2021and2022

"""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import platform
import subprocess
import sys
#import time
import traceback
import pandas as pd
import matplotlib.pyplot as plt
srcdir = os.path.abspath(os.path.dirname(__file__))
libdir = os.path.join(srcdir, 'pylib')
sys.path.append(libdir)
try:
    # pylint: disable=wrong-import-position
    from harisekhon.utils import log
    from harisekhon import CLI
except ImportError as _:
    print(traceback.format_exc(), end='')
    sys.exit(4)

__author__ = 'Hari Sekhon'
__version__ = '0.1'


# pylint: disable=too-few-public-methods
class PlotUKMarriageRates(CLI):

    def __init__(self):
        # Python 2.x
        super(PlotUKMarriageRates, self).__init__()
        # Python 3.x
        # super().__init__()
        self.timeout_default = 0

    # def add_options(self):
    #     super(PlotUKMarriageRates, self).add_options()
    #
    # def process_options(self):
    #     super(PlotUKMarriageRates, self).process_options()

    def run(self):
        if not self.args:
            self.usage("Provide path to datadownload.xlsx")

        file_path = self.args[0]

        if not os.path.isfile(file_path):
            self.usage(f"Invalid argument provided, not a file: {file_path}")

        log.info(f"Loading file: {file_path}")
        xls = pd.ExcelFile(file_path)

        log.info("Parsing xls")
        # Read the relevant sheet and skip the metadata
        df = xls.parse('Figure 2', skiprows=6)

        # Set proper column headers
        df.columns = df.iloc[1]
        df = df[2:]  # Drop the header rows

        # Rename columns for clarity
        df.columns = ['Year', 'Opposite-sex Men', 'Opposite-sex Women', 'Same-sex Men', 'Same-sex Women']

        # Convert data types
        df['Year'] = df['Year'].astype(int)
        for col in ['Opposite-sex Men', 'Opposite-sex Women', 'Same-sex Men', 'Same-sex Women']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        log.info("Plotting")
        plt.figure(figsize=(10, 6))
        plt.plot(df['Year'], df['Opposite-sex Men'], label='Opposite-sex Men')
        plt.plot(df['Year'], df['Opposite-sex Women'], label='Opposite-sex Women')
        plt.plot(df['Year'], df['Same-sex Men'], label='Same-sex Men')
        plt.plot(df['Year'], df['Same-sex Women'], label='Same-sex Women')

        plt.title('Marriage Rates Over Time (England & Wales)')
        plt.xlabel('Year')
        plt.ylabel('Marriage Rate per 1,000 People')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        #plt.show()
        #
        # doesn't show anything because the script finishes before the GUI event loop
        # has time to process and display the window
        #plt.show(block=False)
        #
        # pylint: disable=line-too-long
        #
        # doesn't work even with this hack:
        #
        #    WARNING: NSWindow geometry should only be modified on the main thread! This will raise an exception in the future
        #
        #import threading
        #threading.Thread(target=plt.show).start()
        #sleep_secs = 20
        #log.info(f"Sleeping for {sleep_secs} secs to allow you to see the graph pop-up")
        #time.sleep(sleep_secs)

        image_path = os.path.splitext(file_path)[0] + '.png'
        log.info("Generating output image: {image_path}")

        #if os.path.exists(image_path):
        #    log.warning(f"Image page already exists, skipping recreating for safety: {image_path}")
        #    #plt.close()
        #    return

        # doesn't solve blank png
        #plt.gcf().canvas.draw()

        # results in blank png
        #plt.savefig(image_path)

        fig = plt.gcf()  # draw before saving
        fig.canvas.draw()  # force rendering
        plt.savefig(image_path)

        plt.show()

        if platform.system() == "Darwin":
            # fire and forget
            # pylint: disable=subprocess-run-check
            subprocess.run(['open', image_path])

        #plt.close()


if __name__ == '__main__':
    PlotUKMarriageRates().main()
