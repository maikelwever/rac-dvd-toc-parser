#!/usr/bin/env python3
LICENSE_NOTICE = """
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import json
import os

from argparse import ArgumentParser
from collections import namedtuple


Sectlen = namedtuple('Sectlen', 'num start length')
Location = namedtuple('Location', 'num start')


class TocParser:
    def __init__(self):
        self.args = self.parse_args()
        self.wads = []
        self.vags = []
        self.wads2 = []
        self.video = []
        self.vags2 = []
        self.leveldirs = []

    def parse_args(self):
        parser = ArgumentParser()
        parser.add_argument('disc_location', help="Can be a raw device or path to ISO image")
        parser.add_argument('--dumptoc', help="File to dump ToC to (in JSON format)")
        parser.add_argument('--outdir', help="Folder to output to")
        parser.add_argument('--toc-at', default=1500, type=int, help="Location in sectors for the start of ToC")
        parser.add_argument('--blocksize', default=2048, type=int, help="Size of a sector/block")
        parser.add_argument('--wads-count', default=479, type=int)
        parser.add_argument('--vags-count', default=240, type=int)
        parser.add_argument('--wads2-count', default=165, type=int)
        parser.add_argument('--video-count', default=90, type=int)
        parser.add_argument('--vags2-count', default=900, type=int)
        parser.add_argument('--leveldirs-count', default=38, type=int)
        return parser.parse_args()

    def run(self):
        with open(self.args.disc_location, 'rb') as self.data:
            self.parse_toc()
            if self.args.dumptoc:
                self.dump_toc()

            if self.args.outdir:
                self.copy_data()

    def read_int32(self, pos=None):
        if pos:
            self.data.seek(pos)

        return int.from_bytes(self.data.read(4), byteorder='little')

    def parse_toc(self):
        self.data.seek(self.args.toc_at * self.args.blocksize)
        self.version = self.read_int32()
        self.toc_size = self.read_int32()

        print("Found ToC, version {} with size {}".format(self.version, self.toc_size))

        for i in range(self.args.wads_count):
            info = Sectlen(num=i, start=self.read_int32(), length=self.read_int32())
            self.wads.append(info)

        for i in range(self.args.vags_count):
            location = Location(num=i, start=self.read_int32())
            self.vags.append(location)

        for i in range(self.args.wads2_count):
            info = Sectlen(num=i, start=self.read_int32(), length=self.read_int32())
            self.wads2.append(info)

        for i in range(self.args.video_count):
            info = Sectlen(num=i, start=self.read_int32(), length=self.read_int32())
            self.video.append(info)

        for i in range(self.args.vags2_count):
            location = Location(num=i, start=self.read_int32())
            self.vags2.append(location)

    def parse_vag_header(self):
        """Seek source to correct position before calling this!"""
        header = self.data.read(0x30)  # Header has a static size
        return header, int.from_bytes(header[0x0c:0x10], 'big'), header[0x20:0x30].decode('ascii').strip().strip('\x00')

    def copy_data(self):
        outdir = os.path.abspath(self.args.outdir)
        if not os.path.exists(outdir):
            os.makedirs(outdir)

        waddir = os.path.join(outdir, 'wads')
        if not os.path.exists(waddir):
            os.makedirs(waddir)

        for i, start, length in self.wads:
            if start == 0 or length == 0:
                continue

            filepath = os.path.join(waddir, 'wad_{0}.wad'.format(i))
            self.data.seek(start * self.args.blocksize)
            with open(filepath, 'wb') as f:
                f.write(self.data.read(length * self.args.blocksize))

            print(filepath)

        vagdir = os.path.join(outdir, 'vags')
        if not os.path.exists(vagdir):
            os.makedirs(vagdir)

        for i, start in self.vags:
            if start == 0:
                continue

            self.data.seek(start * self.args.blocksize)
            header, length, filename = self.parse_vag_header()
            filepath = os.path.join(vagdir, '{0}_{1}.vag'.format(filename, i))
            print(filepath)
            with open(filepath, 'wb') as f:
                f.write(header)
                f.write(self.data.read(length))

        wad2dir = os.path.join(outdir, 'wads2')
        if not os.path.exists(wad2dir):
            os.makedirs(wad2dir)

        for i, start, length in self.wads2:
            if start == 0 or length == 0:
                continue

            filepath = os.path.join(wad2dir, 'wad2_{0}.wad'.format(i))
            self.data.seek(start * self.args.blocksize)
            with open(filepath, 'wb') as f:
                f.write(self.data.read(length * self.args.blocksize))

            print(filepath)

        videodir = os.path.join(outdir, 'video')
        if not os.path.exists(videodir):
            os.makedirs(videodir)

        for i, start, length in self.video:
            if start == 0 or length == 0:
                continue

            filepath = os.path.join(videodir, 'video_{0}.bik'.format(i))
            self.data.seek(start * self.args.blocksize)
            with open(filepath, 'wb') as f:
                f.write(self.data.read(length))

            print(filepath)

        vag2dir = os.path.join(outdir, 'vags2')
        if not os.path.exists(vag2dir):
            os.makedirs(vag2dir)

        for i, start in self.vags2:
            if start == 0:
                continue

            self.data.seek(start * self.args.blocksize)
            header, length, filename = self.parse_vag_header()
            filepath = os.path.join(vag2dir, '{0}_{1}.vag2'.format(filename, i))
            with open(filepath, 'wb') as f:
                f.write(header)
                f.write(self.data.read(length))

            print(filepath)

    def dump_toc(self):
        toc = dict(
            version=self.version,
            toc_size=self.toc_size,
            wads=[i._asdict() for i in self.wads],
            wads2=[i._asdict() for i in self.wads2],
            video=[i._asdict() for i in self.video],
            vags=[i._asdict() for i in self.vags],
            vags2=[i._asdict() for i in self.vags2],
        )
        with open(self.args.dumptoc, 'w') as f:
            json.dump(toc, f, indent=4)



def main():
    TocParser().run()


if __name__ == "__main__":
    main()
